"""Unit-of-work factory and schema management over an async engine."""

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from yaddd import EventPublisher
from yaddd_sqlalchemy import SqlSession, SqlTransaction, SqlUnitOfWork

from app.application.uow import OrderRepositories, OrderUnitOfWork
from app.infrastructure.database.models import metadata
from app.infrastructure.database.repositories import SqlOrderRepository


__all__ = ["create_schema", "drop_schema", "make_uow_factory"]


def make_uow_factory(
    session_maker: async_sessionmaker[AsyncSession],
    publisher: EventPublisher,
) -> Callable[[], OrderUnitOfWork]:
    """Return a factory that builds a fresh unit of work.

    A new unit of work per request or command is not a style choice: a
    ``SqlSession`` wraps exactly one ``AsyncSession``, so sharing a unit of
    work between concurrent requests would interleave two transactions on the
    same connection.

    The wiring order matters — session maker, then session, then transaction,
    then the repository bound to that transaction, then the unit of work.
    """

    def factory() -> OrderUnitOfWork:
        transaction = SqlTransaction(SqlSession(session_maker), publisher)
        repos = OrderRepositories(orders=SqlOrderRepository(transaction))
        return SqlUnitOfWork[OrderRepositories](transaction, repos)

    return factory


async def create_schema(engine: AsyncEngine) -> None:
    """Create every table declared in the metadata."""
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)


async def drop_schema(engine: AsyncEngine) -> None:
    """Drop every table declared in the metadata."""
    async with engine.begin() as connection:
        await connection.run_sync(metadata.drop_all)
