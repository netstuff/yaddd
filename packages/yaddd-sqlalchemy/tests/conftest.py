from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from yaddd.domain import AggregateRoot
from yaddd_sqlalchemy import SqlCrudRepository


metadata = MetaData()

orders_table = Table(
    "orders",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("status", String(16), nullable=False),
    Column("total", Integer, nullable=False),
)


class Order(AggregateRoot):
    id: str
    status: str
    total: int


class OrderRepository(SqlCrudRepository[Order]):
    table = orders_table

    def to_domain(self, row: Row[Any]) -> Order:
        return Order(id=str(row.id), status=str(row.status), total=int(row.total))

    def to_row(self, instance: Order) -> dict[str, Any]:
        return {"id": instance.pk, "status": instance.status, "total": instance.total}


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
