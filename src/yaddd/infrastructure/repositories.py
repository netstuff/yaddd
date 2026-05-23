"""Data repositories.

Every repository operates with only one aggregate root and one connector.
"""

from abc import ABC, abstractmethod

from sqlmodel.ext.asyncio.session import AsyncSession
from yaddd.domain.entities.aggregate import AggregateRoot
from yaddd.domain.values import PrimaryKey
from yaddd.infrastructure.connectors import ConnectorBase


class Repository(ABC):
    """Data repository base."""

    def __init__(self, connector: ConnectorBase) -> None:
        """Initialize repository with passed connector."""
        self._connector = connector

    @property
    def conn(self) -> ConnectorBase:
        """Get repository connector."""
        return self._connector


class CrudRepository[T: AggregateRoot](Repository, ABC):
    """Basic repository with CRUD interface."""

    @abstractmethod
    async def get_by_pk(self, pk: PrimaryKey, **kwargs) -> T | None:
        """Get aggregate instance by primary key."""
        ...

    @abstractmethod
    async def create(self, data: dict, **kwargs) -> T:
        """Create aggregate storage item by passed data."""
        ...

    @abstractmethod
    async def read(self, filter: dict, slice: tuple[int, int]=(0, 0), **kwargs) -> list[T]:
        """Get list of aggregates by passed filter."""
        ...

    @abstractmethod
    async def update(self, aggregate: T, **kwargs) -> T:
        """Update aggregate instance."""
        ...

    @abstractmethod
    async def delete(self, filter: dict, **kwargs) -> None:
        """Delete list of data instances found by passed filter."""
        ...


class SqlRepository[T: AggregateRoot](Repository, ABC):
    """Data repository for SQL databases."""

    def __init__(self, session: AsyncSession, **kwargs) -> None:
        """Initialize repository with passed connector."""
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    # @abstractmethod
    # async def find(self, filter: dict, **kwargs) -> T | None:
    #     """Find an aggregate data in database by passed filter."""
    #     ...


class HttpRepository[T: AggregateRoot](Repository, ABC):
    """Data repository for external HTTP services."""
