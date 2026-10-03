"""Unit of Work port."""

from types import TracebackType
from typing import Protocol, Self


__all__ = ["UnitOfWork"]


class UnitOfWork(Protocol):
    """Transactional boundary of a use case: load -> modify -> save.

    Repositories are created over the unit of work's session and never
    commit themselves. Leaving the context without ``commit()`` — or with an
    exception — means rollback.
    """

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None:
        """Persist all changes made within the unit of work."""

    async def rollback(self) -> None:
        """Discard all changes made within the unit of work."""
