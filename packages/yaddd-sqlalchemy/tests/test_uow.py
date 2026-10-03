from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from yaddd.application.uow import UnitOfWork
from yaddd.testing import UnitOfWorkContract
from yaddd_sqlalchemy import SqlUnitOfWork

from conftest import Order, OrderRepository, orders_table


class TestSqlUnitOfWork(UnitOfWorkContract):
    @pytest.fixture
    def uow(self, session: AsyncSession) -> UnitOfWork:
        return SqlUnitOfWork(session)

    @pytest.fixture
    def assert_rolled_back(self, session: AsyncSession) -> Callable[[], Awaitable[None]]:
        async def check() -> None:
            assert not session.in_transaction()
            assert not session.new and not session.dirty

        return check


async def test_commit_persists_changes(engine: AsyncEngine, session: AsyncSession):
    async with SqlUnitOfWork(session) as uow:
        await OrderRepository(session).create(Order(id="order-1", status="new", total=10))
        await uow.commit()

    async with AsyncSession(engine) as verify:
        result = await verify.execute(select(orders_table).where(orders_table.c.id == "order-1"))
        assert result.first() is not None


async def test_exception_inside_context_rolls_back(engine: AsyncEngine, session: AsyncSession):
    with pytest.raises(RuntimeError, match="boom"):
        async with SqlUnitOfWork(session):
            await OrderRepository(session).create(Order(id="order-2", status="new", total=10))
            raise RuntimeError("boom")

    async with AsyncSession(engine) as verify:
        result = await verify.execute(select(orders_table).where(orders_table.c.id == "order-2"))
        assert result.first() is None


async def test_exit_without_commit_rolls_back(engine: AsyncEngine, session: AsyncSession):
    async with SqlUnitOfWork(session):
        await OrderRepository(session).create(Order(id="order-3", status="new", total=10))

    async with AsyncSession(engine) as verify:
        result = await verify.execute(select(orders_table).where(orders_table.c.id == "order-3"))
        assert result.first() is None


async def test_rollback_discards_pending_changes(engine: AsyncEngine, session: AsyncSession):
    async with SqlUnitOfWork(session) as uow:
        await OrderRepository(session).create(Order(id="order-4", status="new", total=10))
        await uow.rollback()

    async with AsyncSession(engine) as verify:
        result = await verify.execute(select(orders_table).where(orders_table.c.id == "order-4"))
        assert result.first() is None
