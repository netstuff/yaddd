"""Integration tests of the worker process.

Consumers are exercised through FastStream's in-memory test broker, so the
subscriber signature, dataclass validation and the projector wiring are verified
without a Redis server. The worker ASGI app is then probed over HTTP exactly the
way a supervisor would.
"""

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from faststream.redis import RedisBroker, TestRedisBroker
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.application.dto import OrderPlacement
from app.application.health import ProbeStatus
from app.application.messaging import EnvelopeKey, EventEnvelope
from app.application.projections import OrderPlacedProjector
from app.composition import build_container
from app.domain.orders.events import OrderPaid, OrderPlaced
from app.infrastructure.config.constants import ConfigDefaults
from app.infrastructure.config.settings import Settings
from app.infrastructure.health import BROKER_CHECK_NAME, DATABASE_CHECK_NAME
from app.infrastructure.messaging.broker import make_broker
from app.presentation.worker.broker import build_worker_app
from app.presentation.worker.constants import WorkerPath
from app.presentation.worker.consumers import make_event_handler, register_consumers
from tests.shared.constants import TEST_BASE_URL, TEST_BROKER_CHANNEL


class RecordingPlacements:
    """In-memory projection store implementing the read-model port."""

    def __init__(self) -> None:
        self.rows: dict[UUID, OrderPlacement] = {}

    async def add(self, placement: OrderPlacement) -> None:
        self.rows[placement.order_id] = placement

    async def find_one(self, order_id: UUID) -> OrderPlacement | None:
        return self.rows.get(order_id)


class RecordingProjector:
    """Projector stand-in recording every envelope it receives."""

    def __init__(self) -> None:
        self.envelopes: list[EventEnvelope] = []

    async def __call__(self, envelope: EventEnvelope) -> None:
        self.envelopes.append(envelope)


def placed_event(order_id: UUID | None = None) -> OrderPlaced:
    """Build a placed event with a valid reference."""
    return OrderPlaced(
        order_id=order_id or uuid4(),
        reference=f"ORD-{uuid4().hex[:8].upper()}",
        total=1999,
    )


@pytest.fixture
def placements() -> RecordingPlacements:
    """Projection store the real projector writes to."""
    return RecordingPlacements()


@pytest.fixture
def test_broker(placements: RecordingPlacements) -> RedisBroker:
    """A real broker object, wired to the projector and never connected.

    ``TestRedisBroker`` patches a broker in place, so subscribers are
    registered on the real object first — exactly as ``register_consumers``
    does in the worker process.
    """
    broker = make_broker(ConfigDefaults.BROKER_URL)
    register_consumers(broker, OrderPlacedProjector(placements), TEST_BROKER_CHANNEL)
    return broker


async def test_handler_forwards_envelopes_to_the_projector() -> None:
    projector = RecordingProjector()
    envelope = EventEnvelope.from_event(placed_event())

    await make_event_handler(projector)(envelope)

    assert projector.envelopes == [envelope]


async def test_subscriber_delivers_an_envelope_to_the_projector(
    test_broker: RedisBroker,
    placements: RecordingPlacements,
) -> None:
    event = placed_event()

    async with TestRedisBroker(test_broker) as broker:
        await broker.publish(EventEnvelope.from_event(event).to_message(), TEST_BROKER_CHANNEL)

    stored = placements.rows.get(event.order_id)
    assert stored is not None
    assert stored.reference == event.reference
    assert stored.total == event.total


async def test_a_malformed_payload_never_reaches_the_projector(
    test_broker: RedisBroker,
    placements: RecordingPlacements,
) -> None:
    async with TestRedisBroker(test_broker) as broker:
        with pytest.raises(ValidationError):
            await broker.publish(
                f'{{"{EnvelopeKey.EVENT_TYPE}": "{OrderPlaced.__name__}"}}',
                TEST_BROKER_CHANNEL,
            )

    assert placements.rows == {}


async def test_unrelated_events_are_delivered_and_ignored(
    test_broker: RedisBroker,
    placements: RecordingPlacements,
) -> None:
    async with TestRedisBroker(test_broker) as broker:
        await broker.publish(
            EventEnvelope.from_event(OrderPaid(order_id=uuid4())).to_message(),
            TEST_BROKER_CHANNEL,
        )

    assert placements.rows == {}


async def test_the_projection_is_idempotent_across_redeliveries(
    test_broker: RedisBroker,
    placements: RecordingPlacements,
) -> None:
    event = placed_event()
    message = EventEnvelope.from_event(event).to_message()

    async with TestRedisBroker(test_broker) as broker:
        await broker.publish(message, TEST_BROKER_CHANNEL)
        await broker.publish(message, TEST_BROKER_CHANNEL)

    assert len(placements.rows) == 1


@pytest.fixture
async def worker_client(settings: Settings, engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """HTTP client bound to the worker ASGI app of this test."""
    container = build_container(settings)
    app = build_worker_app(container)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=TEST_BASE_URL) as client:
        yield client


async def test_worker_liveness_is_ok(worker_client: AsyncClient) -> None:
    response = await worker_client.get(WorkerPath.HEALTH_LIVE)

    assert response.status_code == 200
    assert response.json()["ready"] is True


async def test_worker_health_reports_the_broker(worker_client: AsyncClient) -> None:
    response = await worker_client.get(WorkerPath.HEALTH)

    assert response.status_code == 503
    body = response.json()
    assert {check["name"] for check in body["checks"]} == {DATABASE_CHECK_NAME, BROKER_CHECK_NAME}
    assert next(check for check in body["checks"] if check["name"] == BROKER_CHECK_NAME)["status"] == ProbeStatus.DOWN


async def test_worker_readiness_requires_its_dependencies(worker_client: AsyncClient) -> None:
    assert (await worker_client.get(WorkerPath.HEALTH_READY)).status_code == 503


async def test_worker_serves_its_asyncapi_document(worker_client: AsyncClient) -> None:
    response = await worker_client.get(WorkerPath.ASYNCAPI_JSON, headers={"Accept": "application/json"})

    assert response.status_code == 200
    document = response.json()
    assert document["asyncapi"] == "3.0.0"
    assert document["info"]["title"].endswith(" events")


async def test_asyncapi_documents_the_consumer_and_the_probes(worker_client: AsyncClient) -> None:
    response = await worker_client.get(WorkerPath.ASYNCAPI_JSON, headers={"Accept": "application/json"})
    channels = set(response.json()["channels"])

    assert f"{ConfigDefaults.BROKER_EVENTS_CHANNEL}:HandleEvent" in channels
    assert {"health:HttpChannel", "health_live:HttpChannel", "health_ready:HttpChannel"} <= channels


async def test_worker_serves_the_asyncapi_ui(worker_client: AsyncClient) -> None:
    response = await worker_client.get(WorkerPath.ASYNCAPI)

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
