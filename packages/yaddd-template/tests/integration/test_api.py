"""Integration tests of the HTTP layer.

The real ASGI app is built from the real container against a temporary SQLite
database. Only the ASGI transport is replaced — routers, error handlers,
validation, serialization and the command bus are the production ones.
"""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine
from yaddd import BusinessRuleViolationError, EntityNotFoundError

from app.application.health import ProbeStatus
from app.composition import build_container
from app.domain.orders.constants import OrderStatus
from app.infrastructure.config.settings import Settings
from app.infrastructure.health import BROKER_CHECK_NAME, DATABASE_CHECK_NAME
from app.presentation.api.app import create_app
from app.presentation.api.constants import ApiPath, ApiTag, ErrorPayloadKey, OrderPathParam
from tests.shared.constants import TEST_BASE_URL, TEST_CARD_TOKEN, TEST_REFERENCE, TEST_TOTAL


@pytest.fixture
async def api(settings: Settings, engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """A client bound to the production app wired to the test database.

    The ``engine`` fixture is requested for its side effect: it creates the
    schema before the test and drops it afterwards.
    """
    container = build_container(settings)
    app = create_app(container)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=TEST_BASE_URL) as client:
        yield client


async def test_place_order_returns_201(api: AsyncClient) -> None:
    response = await api.post(ApiPath.ORDERS_PREFIX, json={"reference": TEST_REFERENCE, "total": TEST_TOTAL})

    assert response.status_code == 201
    body = response.json()
    assert body["reference"] == TEST_REFERENCE
    assert body["total"] == TEST_TOTAL
    assert body["status"] == OrderStatus.PLACED


async def test_place_order_rejects_a_malformed_reference(api: AsyncClient) -> None:
    response = await api.post(ApiPath.ORDERS_PREFIX, json={"reference": "nope", "total": TEST_TOTAL})

    assert response.status_code == 422


async def test_place_order_rejects_a_negative_total(api: AsyncClient) -> None:
    response = await api.post(ApiPath.ORDERS_PREFIX, json={"reference": TEST_REFERENCE, "total": -1})

    assert response.status_code == 422


async def test_duplicate_reference_maps_to_conflict(api: AsyncClient) -> None:
    payload = {"reference": "ORD-2B3C4D5E", "total": 500}
    assert (await api.post(ApiPath.ORDERS_PREFIX, json=payload)).status_code == 201

    response = await api.post(ApiPath.ORDERS_PREFIX, json=payload)

    assert response.status_code == 409
    assert response.json()[ErrorPayloadKey.CODE] == IntegrityError.__name__


async def test_pay_marks_the_order_as_paid(api: AsyncClient) -> None:
    created = (await api.post(ApiPath.ORDERS_PREFIX, json={"reference": "ORD-3C4D5E6F", "total": 900})).json()

    response = await api.post(f"{ApiPath.ORDERS_PREFIX}/{created['order_id']}/pay")

    assert response.status_code == 200
    assert response.json()["status"] == OrderStatus.PAID


async def test_pay_twice_maps_to_conflict(api: AsyncClient) -> None:
    created = (await api.post(ApiPath.ORDERS_PREFIX, json={"reference": "ORD-4D5E6F7A", "total": 900})).json()
    await api.post(f"{ApiPath.ORDERS_PREFIX}/{created['order_id']}/pay")

    response = await api.post(f"{ApiPath.ORDERS_PREFIX}/{created['order_id']}/pay")

    assert response.status_code == 409
    assert response.json()[ErrorPayloadKey.CODE] == BusinessRuleViolationError.__name__


async def test_pay_unknown_order_maps_to_404(api: AsyncClient) -> None:
    response = await api.post(f"{ApiPath.ORDERS_PREFIX}/{uuid4()}/pay")

    assert response.status_code == 404
    assert response.json()[ErrorPayloadKey.CODE] == EntityNotFoundError.__name__


async def test_pay_with_a_malformed_identifier_maps_to_422(api: AsyncClient) -> None:
    response = await api.post(f"{ApiPath.ORDERS_PREFIX}/not-a-uuid/pay")

    assert response.status_code == 422


async def test_card_token_is_never_echoed_back(api: AsyncClient) -> None:
    response = await api.post(
        ApiPath.ORDERS_PREFIX,
        json={"reference": "ORD-5E6F7A8B", "total": 900, "card_token": TEST_CARD_TOKEN},
    )

    assert response.status_code == 201
    assert TEST_CARD_TOKEN not in response.text


async def test_liveness_is_ok(api: AsyncClient) -> None:
    response = await api.get(ApiPath.HEALTH_LIVE)

    assert response.status_code == 200
    assert response.json()["ready"] is True


async def test_health_reports_every_dependency(api: AsyncClient) -> None:
    response = await api.get(ApiPath.HEALTH)

    assert response.status_code == 200
    body = response.json()
    assert {check["name"] for check in body["checks"]} == {DATABASE_CHECK_NAME, BROKER_CHECK_NAME}
    assert next(check for check in body["checks"] if check["name"] == DATABASE_CHECK_NAME)["status"] == ProbeStatus.OK


async def test_readiness_reports_503_without_its_dependency(api: AsyncClient) -> None:
    response = await api.get(ApiPath.HEALTH_READY)

    assert response.status_code == 503
    assert response.json()["ready"] is False


async def test_openapi_document_is_served(api: AsyncClient) -> None:
    response = await api.get(ApiPath.OPENAPI)

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert set(paths) >= {
        ApiPath.ORDERS_PREFIX,
        f"{ApiPath.ORDERS_PREFIX}/{{{OrderPathParam.ORDER_ID}}}/pay",
        ApiPath.HEALTH,
        ApiPath.HEALTH_LIVE,
        ApiPath.HEALTH_READY,
    }


async def test_api_routes_are_registered_under_their_prefixes(api: AsyncClient) -> None:
    schema = (await api.get(ApiPath.OPENAPI)).json()

    assert ApiTag.ORDERS in [
        tag for path in schema["paths"].values() for op in path.values() for tag in op.get("tags", [])
    ]
