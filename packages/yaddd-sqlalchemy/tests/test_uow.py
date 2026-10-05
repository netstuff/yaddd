from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from yaddd import DomainEvent, InMemoryEventPublisher
from yaddd_sqlalchemy import SqlSession, SqlTransaction, SqlTransactionBoundRepository, SqlUnitOfWork

from conftest import Order, orders_table


class TxOrderRepository(SqlTransactionBoundRepository[Order]):
    table = orders_table

    def to_domain(self, row) -> Order:
        return Order(id=str(row.id), status=str(row.status), total=int(row.total))

    def to_row(self, instance: Order) -> dict[str, object]:
        return {"id": instance.pk, "status": instance.status, "total": instance.total}


@dataclass
class OrderRepos:
    orders: TxOrderRepository


class OrderPlaced(DomainEvent):
    order_id: str


def build_uow(engine: AsyncEngine) -> SqlUnitOfWork[OrderRepos]:
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    sql_session = SqlSession(session_maker)
    publisher = InMemoryEventPublisher()
    tx = SqlTransaction(sql_session, publisher)
    repos = OrderRepos(orders=TxOrderRepository(tx))
    return SqlUnitOfWork(tx, repos)


async def test_uow_exposes_repositories(engine: AsyncEngine):
    uow = build_uow(engine)
    async with uow:
        assert isinstance(uow.repos.orders, TxOrderRepository)


async def test_commit_persists_changes(engine: AsyncEngine):
    uow = build_uow(engine)
    order_id = uuid4().hex

    async with uow:
        order = Order(id=order_id, status="new", total=10)
        await uow.repos.orders.create(order)
        await uow.commit()

    async with async_sessionmaker(engine, expire_on_commit=False)() as verify:
        result = await verify.execute(select(orders_table).where(orders_table.c.id == order_id))
        assert result.first() is not None


async def test_exit_without_commit_rolls_back(engine: AsyncEngine):
    uow = build_uow(engine)
    order_id = uuid4().hex

    async with uow:
        order = Order(id=order_id, status="new", total=10)
        await uow.repos.orders.create(order)

    async with async_sessionmaker(engine, expire_on_commit=False)() as verify:
        result = await verify.execute(select(orders_table).where(orders_table.c.id == order_id))
        assert result.first() is None


async def test_exception_inside_context_rolls_back(engine: AsyncEngine):
    uow = build_uow(engine)
    order_id = uuid4().hex

    with pytest.raises(RuntimeError, match="boom"):
        async with uow:
            order = Order(id=order_id, status="new", total=10)
            await uow.repos.orders.create(order)
            raise RuntimeError("boom")

    async with async_sessionmaker(engine, expire_on_commit=False)() as verify:
        result = await verify.execute(select(orders_table).where(orders_table.c.id == order_id))
        assert result.first() is None


async def test_rollback_discards_pending_changes(engine: AsyncEngine):
    uow = build_uow(engine)
    order_id = uuid4().hex

    async with uow:
        order = Order(id=order_id, status="new", total=10)
        await uow.repos.orders.create(order)
        await uow.rollback()

    async with async_sessionmaker(engine, expire_on_commit=False)() as verify:
        result = await verify.execute(select(orders_table).where(orders_table.c.id == order_id))
        assert result.first() is None


async def test_commit_publishes_tracked_events(engine: AsyncEngine):
    publisher = InMemoryEventPublisher()
    events: list[DomainEvent] = []

    async def collect(event: DomainEvent) -> None:
        events.append(event)

    publisher.subscribe(OrderPlaced, collect)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    sql_session = SqlSession(session_maker)
    tx = SqlTransaction(sql_session, publisher)
    repos = OrderRepos(orders=TxOrderRepository(tx))
    uow = SqlUnitOfWork(tx, repos)

    async with uow:
        order = Order(id=uuid4().hex, status="new", total=10)
        order.add_event(OrderPlaced(order_id=order.pk))
        await uow.repos.orders.create(order)
        await uow.commit()

    assert len(events) == 1
    assert isinstance(events[0], OrderPlaced)
