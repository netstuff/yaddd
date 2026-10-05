"""SQLAlchemy Core implementation of the ``CrudRepository`` port."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from sqlalchemy import Column, Table, delete, insert, select, update
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from yaddd.domain.entities import AggregateRoot, PrimaryKey
from yaddd.domain.repositories import CrudRepository
from yaddd.exceptions import EntityNotFoundError

from yaddd_sqlalchemy.session import SqlSession, SqlTransaction


__all__ = ["SqlCrudRepository", "SqlTransactionBoundRepository"]


class SqlCrudRepository[T: AggregateRoot](CrudRepository[T], ABC):
    """SQLAlchemy Core-based repository for a single aggregate type.

    No ORM declarative opinions: the subclass declares a Core ``table`` and
    the mapping between rows and aggregates. The repository never commits —
    transaction boundaries belong to ``SqlUnitOfWork``.

    Primary keys must be single-column, and ``pk`` values must be natively
    bindable by the primary-key column type (use a ``TypeDecorator`` column
    or string/integer primary keys otherwise).

    Example:
        class OrderRepository(SqlCrudRepository[Order]):
            table = orders_table

            def to_domain(self, row: Row[Any]) -> Order:
                return Order(id=row.id, status=row.status, total=row.total)

            def to_row(self, instance: Order) -> dict[str, Any]:
                return {"id": instance.pk, "status": instance.status, "total": instance.total}
    """

    table: ClassVar[Table]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    def to_domain(self, row: Row[Any]) -> T:
        """Reconstitute the aggregate from a table row."""

    @abstractmethod
    def to_row(self, instance: T) -> dict[str, Any]:
        """Map the aggregate to a dict of column values."""

    @property
    def _pk_column(self) -> Column[Any]:
        columns = list(self.table.primary_key.columns)
        if len(columns) != 1:
            raise NotImplementedError("SqlCrudRepository supports single-column primary keys only")
        return columns[0]

    async def get(self, pk: PrimaryKey) -> T | None:
        result = await self._session.execute(select(self.table).where(self._pk_column == pk))
        row = result.first()
        return None if row is None else self.to_domain(row)

    async def read(self, filter: dict[str, Any] | None = None, *, slice: tuple[int, int] = (0, 0)) -> list[T]:
        stmt = select(self.table)
        for key, value in (filter or {}).items():
            stmt = stmt.where(self.table.c[key] == value)
        offset, limit = slice
        stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return [self.to_domain(row) for row in result.all()]

    async def create(self, instance: T) -> T:
        await self._session.execute(insert(self.table).values(**self.to_row(instance)))
        return instance

    async def update(self, instance: T) -> T:
        if await self.get(instance.pk) is None:
            raise EntityNotFoundError(f"{type(instance).__name__}({instance.pk})")
        stmt = update(self.table).where(self._pk_column == instance.pk).values(**self.to_row(instance))
        await self._session.execute(stmt)
        return instance

    async def delete(self, pk: PrimaryKey) -> None:
        await self._session.execute(delete(self.table).where(self._pk_column == pk))


class SqlTransactionBoundRepository[T: AggregateRoot](SqlCrudRepository[T], ABC):
    """SQLAlchemy repository bound to a ``SqlTransaction``.

    The SQLAlchemy session is resolved lazily from the active transaction, so
    the repository can be constructed before the transaction context is
    entered. Created and updated aggregates are automatically tracked for
    event publication on commit.
    """

    def __init__(self, transaction: SqlTransaction) -> None:
        self._transaction = transaction

    @property
    def _session(self) -> AsyncSession:
        return self._transaction.session.session

    async def create(self, instance: T) -> T:
        result = await super().create(instance)
        self._transaction.track(instance)
        return result

    async def update(self, instance: T) -> T:
        result = await super().update(instance)
        self._transaction.track(instance)
        return result
