"""Repository implementations and read-model ports."""

from typing import Any, Protocol

from yaddd.domain.entities import AggregateRoot, PrimaryKey
from yaddd.domain.repositories import CrudRepository
from yaddd.exceptions import EntityNotFoundError
from yaddd.infrastructure.read_models import ReadModel


__all__ = ["InMemoryCrudRepository", "ReadModelRepository"]


class InMemoryCrudRepository[T: AggregateRoot](CrudRepository[T]):
    """Dict-backed implementation of the ``CrudRepository`` port.

    Useful for tests, prototypes and simple applications. ``create`` inserts
    or replaces; ``update`` requires the aggregate to exist; ``delete`` is
    idempotent.
    """

    def __init__(self, storage: dict[PrimaryKey, T] | None = None) -> None:
        self._storage: dict[PrimaryKey, T] = {} if storage is None else storage

    async def get(self, pk: PrimaryKey) -> T | None:
        return self._storage.get(pk)

    async def read(self, filter: dict[str, Any] | None = None, *, slice: tuple[int, int] = (0, 0)) -> list[T]:
        items = list(self._storage.values())
        if filter:
            items = [item for item in items if all(getattr(item, key, None) == value for key, value in filter.items())]
        offset, limit = slice
        return items[offset:] if limit == 0 else items[offset : offset + limit]

    async def create(self, instance: T) -> T:
        self._storage[instance.pk] = instance
        return instance

    async def update(self, instance: T) -> T:
        if instance.pk not in self._storage:
            raise EntityNotFoundError(f"{type(instance).__name__}({instance.pk})")
        self._storage[instance.pk] = instance
        return instance

    async def delete(self, pk: PrimaryKey) -> None:
        self._storage.pop(pk, None)


class ReadModelRepository[M: ReadModel](Protocol):
    """Read-only access to read models."""

    async def find(self, filter: dict[str, Any] | None = None, *, slice: tuple[int, int] = (0, 0)) -> list[M]:
        """Return read models matching the filter.

        ``slice`` is an ``(offset, limit)`` pair; ``limit=0`` means no limit.
        """
        ...

    async def find_one(self, pk: PrimaryKey) -> M | None:
        """Return a single read model by its primary key, or None."""
        ...
