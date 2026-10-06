"""Shared fixtures.

Every test runs against a throwaway SQLite file: no shared state, no ordering
surprises, and ``BEGIN``/``ROLLBACK`` behave like a real server database
instead of an in-memory shortcut.
"""

from collections.abc import AsyncIterator, Callable
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from yaddd import DomainEvent, EventPublisher, InMemoryEventPublisher

from app.application.uow import OrderUnitOfWork
from app.infrastructure.config.settings import Settings
from app.infrastructure.database.uow import create_schema, drop_schema, make_uow_factory
from tests.shared.constants import TEST_DB_FILENAME


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointing at a database file used by this test only."""
    return Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / TEST_DB_FILENAME}", probe_timeout=1.0)


@pytest.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """An engine whose schema is created before and dropped after the test."""
    created = create_async_engine(settings.database_url, future=True)
    await create_schema(created)
    try:
        yield created
    finally:
        await drop_schema(created)
        await created.dispose()


@pytest.fixture
def session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Session factory bound to the test engine."""
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def publisher() -> InMemoryEventPublisher:
    """An in-process publisher collecting what the unit of work emits."""
    return InMemoryEventPublisher()


@pytest.fixture
def make_uow(
    session_maker: async_sessionmaker[AsyncSession],
    publisher: EventPublisher,
) -> Callable[[], OrderUnitOfWork]:
    """Factory of fresh units of work, wired exactly like production."""
    return make_uow_factory(session_maker, publisher)


@pytest.fixture
async def published(publisher: InMemoryEventPublisher) -> list[DomainEvent]:
    """Collect every published event, in publication order."""
    collected: list[DomainEvent] = []

    async def collect(event: DomainEvent) -> None:
        collected.append(event)

    publisher.subscribe(DomainEvent, collect)
    return collected
