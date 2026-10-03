"""Repository ports.

The contracts live in the domain layer; implementations — in infrastructure
(Persistence Ignorance).
"""

from typing import Any, Protocol

from yaddd.domain.entities import AggregateRoot, PrimaryKey


__all__ = ["CrudRepository", "Repository"]


class Repository[T: AggregateRoot](Protocol):
    """Storage port for a single aggregate type."""


class CrudRepository[T: AggregateRoot](Repository[T], Protocol):
    """Storage port with a basic CRUD interface.

    Repositories never manage transactions: commit/rollback is the
    responsibility of ``UnitOfWork`` — and never publish domain events.
    """

    async def get(self, pk: PrimaryKey) -> T | None:
        """Return the aggregate by its primary key, or None."""
        ...

    async def read(self, filter: dict[str, Any] | None = None, *, slice: tuple[int, int] = (0, 0)) -> list[T]:
        """Return aggregates matching the filter.

        ``slice`` is an ``(offset, limit)`` pair; ``limit=0`` means no limit.
        """
        ...

    async def create(self, instance: T) -> T:
        """Store a new aggregate."""
        ...

    async def update(self, instance: T) -> T:
        """Replace the stored aggregate. Raises EntityNotFoundError if absent."""
        ...

    async def delete(self, pk: PrimaryKey) -> None:
        """Delete the aggregate by its primary key. Idempotent."""
        ...
