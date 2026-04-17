"""Data repositories.

Every repository operates with only one aggregate root and one connector.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from functools import singledispatchmethod
from typing import Final, TypeAlias
from uuid import UUID

from yaddd.domain.aggregate import AggregateRoot
from yaddd.domain.values import PrimaryKey
from yaddd.infrastructure.connectors import ConnectorBase


class Repository(ABC):
    """Data repository base."""

    Aggregate: AggregateRoot

    def __init__(self, connector: ConnectorBase) -> None:
        """Initialize repository with passed connector."""
        self._connector = connector


class CrudRepository(Repository, ABC):
    """Basic repository with CRUD interface."""

    @abstractmethod
    def get(self, pk: PrimaryKey, **kwargs) -> AggregateRoot | None:
        """Get aggregate by primary key."""

    @abstractmethod
    def create(self, aggregate: AggregateRoot, **kwargs) -> AggregateRoot:
        """Create data by passed instance."""

    @abstractmethod
    def read(self, filter: dict, slice: tuple[int, int]=(0, 0), **kwargs) -> list[AggregateRoot]:
        """Get list of aggregates by passed filter."""

    @abstractmethod
    def update(self, aggregate: AggregateRoot, **kwargs) -> AggregateRoot:
        """Update aggregate instance."""

    @abstractmethod
    def delete(self, filter: dict, **kwargs) -> None:
        """Delete list of data instances found by passed filter."""


class SqlRepository(Repository, ABC):
    """Data repository for SQL databases."""

    @abstractmethod
    def find(self, filter: dict, **kwargs) -> AggregateRoot | None:
        """Find a row in database by passed filter."""


class HttpRepository(Repository, ABC):
    """Data repository for external HTTP services."""
