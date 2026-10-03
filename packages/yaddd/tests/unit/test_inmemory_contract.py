from collections.abc import Callable
from uuid import UUID, uuid4

import pytest

from yaddd.domain import AggregateRoot, CrudRepository
from yaddd.infrastructure import InMemoryCrudRepository
from yaddd.testing import CrudRepositoryContract


class Order(AggregateRoot):
    id: UUID
    status: str
    total: int


class TestInMemoryCrudRepository(CrudRepositoryContract):
    @pytest.fixture
    def repo(self) -> CrudRepository[Order]:
        return InMemoryCrudRepository()

    @pytest.fixture
    def aggregate_factory(self) -> Callable[[], Order]:
        def make() -> Order:
            token = uuid4()
            return Order(id=token, status=f"status-{token.hex[:8]}", total=token.int % 1000)

        return make
