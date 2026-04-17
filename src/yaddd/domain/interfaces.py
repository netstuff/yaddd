"""Domain repository interfaces."""

from typing import Protocol
from uuid import UUID


class DomainRepository[T](Protocol):
    """Domain repository base."""


class CrudRepoInterface[T](DomainRepository, Protocol):
    """Domain repository with basic CRUD-interface."""

    def get(self, pk: UUID) -> T:
        """Get an aggregate instance by its own primary key."""
        ...

    def read(self, filter: dict | None, **kwargs: dict) -> list[T]:
        """Get list of aggregate interfaces by passed filter."""
        ...

    def create(self, instance: T) -> T:
        """Create a data record from aggregate instance."""
        ...

    def update(self, instance: T) -> T:
        """Update a data record with modified aggregate instance."""
        ...

    def delete(self, pk: UUID) -> None:
        """Delete a data record by an aggregate primary key."""
        ...
