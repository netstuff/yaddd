"""Application-level transactional boundary.

The ``Transaction`` protocol hides the mechanics of committing work and
publishing domain events. Handlers declare it as a dependency and use it to
mark the atomic boundary of a use case.

Tracked aggregates have their events pulled and published automatically when
``commit()`` is called. Concrete implementations live in the infrastructure
layer.
"""

from typing import Protocol, Self

from yaddd.domain.entities import AggregateRoot


__all__ = ["Transaction"]


class Transaction(Protocol):
    """Atomic boundary for a command handler.

    ``track`` registers aggregates whose events should be published on commit.
    ``commit`` persists the work and publishes the collected events.
    ``rollback`` discards the work. The async context manager opens and closes
    the underlying resource; exiting without an explicit ``commit`` rolls back.
    """

    def track(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate whose events should be published on commit."""
        ...

    async def commit(self) -> None:
        """Persist the work and publish events from tracked aggregates."""
        ...

    async def rollback(self) -> None:
        """Discard all changes made within the transaction."""
        ...

    async def __aenter__(self) -> Self:
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        ...
