"""Contract tests: this slice against the executable yaddd specifications.

Inheriting from a contract is how a template proves its adapters really honour
the ports: when ``yaddd`` strengthens a guarantee, these tests fail until the
adapters catch up. Only the fixtures are local; every assertion belongs to
``yaddd.testing``.
"""

from collections.abc import AsyncIterator, Callable
from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic import BaseModel, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from yaddd import AggregateRoot, CrudRepository, InMemoryEventPublisher, UnitOfWork, ValueObject
from yaddd.testing import CrudRepositoryContract, UnitOfWorkContract, VoSerializationContract
from yaddd_sqlalchemy import SqlSession, SqlTransaction, SqlUnitOfWork

from app.application.uow import OrderRepositories
from app.domain.orders.aggregates.order import Order
from app.domain.orders.value_objects import CardToken, Money, OrderReference
from app.infrastructure.database.repositories import SqlOrderRepository
from tests.shared.constants import TEST_CARD_TOKEN, TEST_REFERENCE


def _transaction(session_maker: async_sessionmaker[AsyncSession]) -> SqlTransaction:
    """Build the transaction an adapter is bound to, as production does."""
    return SqlTransaction(SqlSession(session_maker), InMemoryEventPublisher())


def new_order() -> Order:
    """A unique order: primary key *and* reference differ on every call."""
    return Order(
        id=uuid4(),
        reference=OrderReference(f"ORD-{uuid4().hex[:8].upper()}"),
        total=Money(1999),
    )


class TestSqlOrderRepository(CrudRepositoryContract):
    """The order repository must behave like any ``CrudRepository``."""

    @pytest.fixture
    async def repo(self, session_maker: async_sessionmaker[AsyncSession]) -> AsyncIterator[CrudRepository[Any]]:
        """A repository bound to an open transaction over the test database.

        The transaction must already be entered: a transaction-bound repository
        resolves its session lazily and refuses to work outside one.
        """
        transaction = _transaction(session_maker)
        async with transaction:
            yield SqlOrderRepository(transaction)

    @pytest.fixture
    def aggregate_factory(self) -> Callable[[], AggregateRoot]:
        """Produce a fresh, unique order on every call."""
        return new_order


class TestOrderUnitOfWork(UnitOfWorkContract):
    """The unit of work must commit, roll back and propagate exceptions."""

    @pytest.fixture
    def uow(self, session_maker: async_sessionmaker[AsyncSession]) -> UnitOfWork[Any]:
        """A fresh unit of work over the test database."""
        transaction = _transaction(session_maker)
        repos = OrderRepositories(orders=SqlOrderRepository(transaction))
        return SqlUnitOfWork[OrderRepositories](transaction, repos)


class TestOrderReferenceSerialization(VoSerializationContract):
    """``OrderReference`` must behave as a first-class pydantic field type."""

    @pytest.fixture
    def vo(self) -> ValueObject[Any]:
        return OrderReference(TEST_REFERENCE)

    @pytest.fixture
    def invalid_raw(self) -> Any:
        return "nope"

    @pytest.fixture
    def dump(self) -> Callable[[ValueObject[Any]], Any]:
        adapter: TypeAdapter[OrderReference] = TypeAdapter(OrderReference)
        return lambda vo: adapter.dump_python(cast("OrderReference", vo))

    @pytest.fixture
    def load(self) -> Callable[[Any], ValueObject[Any]]:
        adapter: TypeAdapter[OrderReference] = TypeAdapter(OrderReference)
        return lambda raw: adapter.validate_python(raw)

    @pytest.fixture
    def sensitive_vo(self) -> ValueObject[Any]:
        return CardToken(TEST_CARD_TOKEN)

    @pytest.fixture
    def container_repr(self) -> Callable[[ValueObject[Any]], str]:
        class Wrapper(BaseModel):
            value: CardToken

        return lambda vo: repr(Wrapper(value=cast(CardToken, vo)))
