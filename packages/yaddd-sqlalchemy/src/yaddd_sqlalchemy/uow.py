"""``UnitOfWork`` implementation over a SQLAlchemy transaction."""

from types import TracebackType
from typing import Self, TypeVar

from yaddd.application.uow import UnitOfWork
from yaddd.domain.entities import AggregateRoot

from yaddd_sqlalchemy.session import SqlTransaction


R = TypeVar("R")

__all__ = ["SqlUnitOfWork"]


class SqlUnitOfWork[R](UnitOfWork[R]):
    """Unit of work over a single SQLAlchemy transaction.

    Repositories in ``repos`` share the underlying ``SqlTransaction``.
    ``commit()`` persists the work and publishes domain events from tracked
    aggregates. Exiting the context without ``commit()`` — or with an
    exception — rolls back.
    """

    def __init__(self, transaction: SqlTransaction, repos: R) -> None:
        self._transaction = transaction
        self._repos = repos

    @property
    def repos(self) -> R:
        """Repository bundle used within this unit of work."""
        return self._repos

    def track(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate whose events should be published on commit."""
        self._transaction.track(aggregate)

    async def __aenter__(self) -> Self:
        await self._transaction.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._transaction.__aexit__(exc_type, exc_value, traceback)

    async def commit(self) -> None:
        """Persist all tracked changes and publish domain events."""
        await self._transaction.commit()

    async def rollback(self) -> None:
        """Discard all tracked changes."""
        await self._transaction.rollback()
