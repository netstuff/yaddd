"""SQLAlchemy implementation of the application ``Session`` protocol."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from yaddd.application.session import Session
from yaddd.infrastructure.transaction import BaseTransaction


__all__ = ["SqlSession", "SqlTransaction"]


class SqlSession(Session):
    """Transactional session over a SQLAlchemy ``AsyncSession``."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        """The currently active SQLAlchemy session."""
        if self._session is None:
            raise RuntimeError("SQLAlchemy session is not active")
        return self._session

    async def begin(self) -> None:
        """Open a new SQLAlchemy session."""
        self._session = self._session_maker()
        await self._session.__aenter__()

    async def commit(self) -> None:
        """Commit the current session."""
        if self._session is not None:
            await self._session.commit()

    async def rollback(self) -> None:
        """Roll back the current session."""
        if self._session is not None:
            await self._session.rollback()

    async def close(self) -> None:
        """Close the current session."""
        if self._session is not None:
            await self._session.__aexit__(None, None, None)
            self._session = None


class SqlTransaction(BaseTransaction[SqlSession]):
    """Transaction bound to a single SQLAlchemy session."""
