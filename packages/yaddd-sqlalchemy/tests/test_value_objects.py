import pytest
from sqlalchemy import Column, MetaData, String, Table, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from yaddd.domain import ValueObject
from yaddd.exceptions import ValidationError
from yaddd_sqlalchemy import VOTypeDecorator


class Email(ValueObject[str]):
    @classmethod
    def validate(cls, value: str) -> str:
        if "@" not in value:
            raise ValidationError(f"not an email: {value}")
        return value.lower()


class EmailType(VOTypeDecorator):
    impl = String(255)
    cache_ok = True
    vo_class = Email


contacts_metadata = MetaData()

contacts_table = Table(
    "contacts",
    contacts_metadata,
    Column("id", String(32), primary_key=True),
    Column("email", EmailType, nullable=True),
)


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(contacts_metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def test_value_object_round_trip(session: AsyncSession):
    await session.execute(insert(contacts_table).values(id="c-1", email=Email("User@Example.com")))
    await session.commit()

    result = await session.execute(select(contacts_table.c.email).where(contacts_table.c.id == "c-1"))
    loaded = result.scalar_one()

    assert isinstance(loaded, Email)
    assert loaded == Email("user@example.com")


async def test_none_round_trip(session: AsyncSession):
    await session.execute(insert(contacts_table).values(id="c-2", email=None))
    await session.commit()

    result = await session.execute(select(contacts_table.c.email).where(contacts_table.c.id == "c-2"))
    assert result.scalar_one() is None
