"""Unit tests of the operator CLI and the event drain.

The CLI owns its event loop, so these tests are synchronous: ``WorkerCli.run``
is called exactly as the console script calls it, and async helpers are driven
through ``asyncio.run``.
"""

import asyncio
import json
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.application.messaging import EnvelopeKey, EventEnvelope
from app.composition import Container, build_container
from app.domain.orders.constants import OrderStatus
from app.domain.orders.events import OrderPlaced
from app.infrastructure.config.settings import Settings
from app.infrastructure.database.models import orders_table
from app.infrastructure.database.uow import drop_schema
from app.infrastructure.health import BROKER_CHECK_NAME, DATABASE_CHECK_NAME
from app.presentation.worker.cli import WorkerCli, build_parser
from app.presentation.worker.constants import WorkerCommand, WorkerError
from app.presentation.worker.drain import decode_payload, drain_events
from tests.shared.constants import (
    TEST_BROKER_CHANNEL,
    TEST_REFERENCE,
    TEST_TOTAL,
    UNREACHABLE_BROKER_URL,
)


@pytest.fixture
def container(settings: Settings) -> Container:
    """A container bound to the test database."""
    return build_container(settings)


def order_count(session_maker: async_sessionmaker[AsyncSession]) -> int:
    """How many order rows the database holds."""
    return asyncio.run(_order_count(session_maker))


def table_exists(session_maker: async_sessionmaker[AsyncSession]) -> bool:
    """Whether the ``orders`` table can be read."""
    return asyncio.run(_table_exists(session_maker))


def test_parser_rejects_an_unknown_command() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["nope"])


def test_place_order_requires_a_reference() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([WorkerCommand.PLACE_ORDER, "--total", str(TEST_TOTAL)])


def test_drain_defaults_to_five_seconds() -> None:
    assert build_parser().parse_args([WorkerCommand.DRAIN]).seconds == 5.0


def test_migrate_creates_the_schema(
    container: Container,
    engine: AsyncEngine,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    asyncio.run(drop_schema(engine))

    assert WorkerCli(container).run([WorkerCommand.MIGRATE]) == 0
    assert table_exists(session_maker)


def test_migrate_is_idempotent(container: Container, session_maker: async_sessionmaker[AsyncSession]) -> None:
    assert WorkerCli(container).run([WorkerCommand.MIGRATE]) == 0
    assert WorkerCli(container).run([WorkerCommand.MIGRATE]) == 0
    assert table_exists(session_maker)


def test_drop_all_removes_the_schema(container: Container, session_maker: async_sessionmaker[AsyncSession]) -> None:
    WorkerCli(container).run([WorkerCommand.MIGRATE])

    assert WorkerCli(container).run([WorkerCommand.DROP_ALL]) == 0
    assert not table_exists(session_maker)


def test_health_exits_nonzero_when_not_ready(container: Container, capsys: pytest.CaptureFixture[str]) -> None:
    code = WorkerCli(container).run([WorkerCommand.HEALTH])

    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["ready"] is False
    assert {check["name"] for check in payload["checks"]} == {DATABASE_CHECK_NAME, BROKER_CHECK_NAME}


def test_place_order_writes_an_order(
    container: Container,
    capsys: pytest.CaptureFixture[str],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    exit_code = WorkerCli(container).run(
        [WorkerCommand.PLACE_ORDER, "--reference", TEST_REFERENCE, "--total", str(TEST_TOTAL)]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["reference"] == TEST_REFERENCE
    assert payload["status"] == OrderStatus.PLACED
    assert order_count(session_maker) == 1


def test_place_order_rejects_a_malformed_reference(container: Container, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = WorkerCli(container).run([WorkerCommand.PLACE_ORDER, "--reference", "nope", "--total", "10"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.startswith(WorkerError.STDERR_PREFIX)


def test_place_order_reports_a_duplicate_reference(
    container: Container,
    capsys: pytest.CaptureFixture[str],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    WorkerCli(container).run([WorkerCommand.MIGRATE])
    WorkerCli(container).run([WorkerCommand.PLACE_ORDER, "--reference", TEST_REFERENCE, "--total", str(TEST_TOTAL)])
    capsys.readouterr()

    exit_code = WorkerCli(container).run([WorkerCommand.PLACE_ORDER, "--reference", TEST_REFERENCE, "--total", "500"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == f"{WorkerError.STDERR_PREFIX} {WorkerError.DUPLICATE_UNIQUE_VALUE}\n"
    assert order_count(session_maker) == 1


async def test_drain_returns_nothing_when_redis_is_unreachable() -> None:
    assert await drain_events(UNREACHABLE_BROKER_URL, TEST_BROKER_CHANNEL, 0.2) == []


def test_decode_skips_payloads_it_cannot_read() -> None:
    assert decode_payload(None) is None
    assert decode_payload(42) is None
    assert decode_payload(f'{{"{EnvelopeKey.EVENT_TYPE}": "{OrderPlaced.__name__}"}}') is None


def test_decode_reads_a_wire_envelope() -> None:
    envelope = EventEnvelope.from_event(OrderPlaced(order_id=uuid4(), reference="ORD-1A2B3C4D", total=1))

    assert decode_payload(json.dumps(envelope.to_message())) == envelope
    assert decode_payload(json.dumps(envelope.to_message()).encode()) == envelope


async def _order_count(session_maker: async_sessionmaker[AsyncSession]) -> int:
    async with session_maker() as session:
        result = await session.execute(select(orders_table))
        return len(result.fetchall())


async def _table_exists(session_maker: async_sessionmaker[AsyncSession]) -> bool:
    try:
        await _order_count(session_maker)
    except SQLAlchemyError:
        return False
    return True
