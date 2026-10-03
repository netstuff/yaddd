"""``UnitOfWork`` implementation over a SQLAlchemy ``AsyncSession``."""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession
from yaddd.application.uow import UnitOfWork


__all__ = ["SqlUnitOfWork"]


class SqlUnitOfWork(UnitOfWork):
    """Transactional boundary over a single ``AsyncSession``.

    ``commit()`` flushes and commits the session. Leaving the context without
    a commit — or with an exception — rolls back; the session is always
    closed on exit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None or not self._committed:
                await self.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        """Persist all changes made within the unit of work."""
        await self._session.commit()
        self._committed = True

    async def rollback(self) -> None:
        """Discard all changes made within the unit of work."""
        await self._session.rollback()
