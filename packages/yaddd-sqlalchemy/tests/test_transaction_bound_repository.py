from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from yaddd import DomainEvent, InMemoryEventPublisher
from yaddd_sqlalchemy import SqlSession, SqlTransaction, SqlTransactionBoundRepository

from conftest import Order, orders_table


class OrderPlaced(DomainEvent):
    order_id: str


class TxOrderRepository(SqlTransactionBoundRepository[Order]):
    table = orders_table

    def to_domain(self, row) -> Order:
        return Order(id=str(row.id), status=str(row.status), total=int(row.total))

    def to_row(self, instance: Order) -> dict[str, object]:
        return {"id": instance.pk, "status": instance.status, "total": instance.total}


@pytest.fixture
def session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_create_tracks_aggregate_and_publishes_event(session_maker):
    publisher = InMemoryEventPublisher()
    events: list[DomainEvent] = []

    async def collect(event: DomainEvent) -> None:
        events.append(event)

    publisher.subscribe(OrderPlaced, collect)

    sql_session = SqlSession(session_maker)
    tx = SqlTransaction(sql_session, publisher)
    repo = TxOrderRepository(tx)

    async with tx:
        order = Order(id=uuid4().hex, status="new", total=42)
        order.add_event(OrderPlaced(order_id=order.pk))
        await repo.create(order)
        await tx.commit()

    assert len(events) == 1
    assert isinstance(events[0], OrderPlaced)
    assert events[0].order_id == order.pk

    async with session_maker() as session:
        row = (await session.execute(select(orders_table).where(orders_table.c.id == order.pk))).one()
        assert row.total == 42


async def test_rollback_does_not_publish_event(session_maker):
    publisher = InMemoryEventPublisher()
    events: list[DomainEvent] = []

    async def collect(event: DomainEvent) -> None:
        events.append(event)

    publisher.subscribe(OrderPlaced, collect)

    sql_session = SqlSession(session_maker)
    tx = SqlTransaction(sql_session, publisher)
    repo = TxOrderRepository(tx)

    with pytest.raises(RuntimeError):
        async with tx:
            order = Order(id=uuid4().hex, status="new", total=10)
            order.add_event(OrderPlaced(order_id=order.pk))
            await repo.create(order)
            raise RuntimeError("boom")

    assert len(events) == 0

    async with session_maker() as session:
        row = (await session.execute(select(orders_table).where(orders_table.c.id == order.pk))).one_or_none()
        assert row is None
