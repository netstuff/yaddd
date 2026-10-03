from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from yaddd.domain import AggregateRoot, CrudRepository
from yaddd.testing import CrudRepositoryContract

from conftest import Order, OrderRepository


class TestSqlCrudRepository(CrudRepositoryContract):
    """The contract suite proves port conformance against in-memory sqlite."""

    @pytest.fixture
    def repo(self, session: AsyncSession) -> CrudRepository[Order]:
        return OrderRepository(session)

    @pytest.fixture
    def aggregate_factory(self) -> Callable[[], Order]:
        def make() -> Order:
            token = uuid4().hex
            return Order(id=token, status=f"status-{token[:8]}", total=int(token[:6], 16) % 1000)

        return make


async def test_get_missing_returns_none_for_unknown_pk(session: AsyncSession):
    repo: CrudRepository[Any] = OrderRepository(session)

    assert await repo.get("no-such-id") is None
