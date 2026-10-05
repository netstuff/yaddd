"""Unit of Work port."""

from types import TracebackType
from typing import Protocol, Self, TypeVar

from yaddd.domain.entities import AggregateRoot


R = TypeVar("R")

__all__ = ["UnitOfWork"]


class UnitOfWork[R](Protocol):
    """Coordinates changes to multiple aggregates within one business operation.

    Repositories are obtained through ``repos`` and share the same
    transactional boundary. Aggregates whose events must be published on
    commit are tracked explicitly via ``track`` (usually by repositories
    themselves). Exiting the context without ``commit()`` — or with an
    exception — means rollback.
    """

    @property
    def repos(self) -> R:
        """Repository bundle used within this unit of work."""
        ...

    def track(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate whose events should be published on commit."""
        ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None:
        """Persist all tracked changes and publish domain events."""

    async def rollback(self) -> None:
        """Discard all tracked changes."""
