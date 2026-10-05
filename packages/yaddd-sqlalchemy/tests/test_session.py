import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from yaddd_sqlalchemy import SqlSession


async def test_sql_session_lifecycle(engine):
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    sql_session = SqlSession(session_maker)

    with pytest.raises(RuntimeError):
        _ = sql_session.session

    await sql_session.begin()
    assert sql_session.session is not None

    await sql_session.commit()
    await sql_session.close()

    with pytest.raises(RuntimeError):
        _ = sql_session.session


async def test_sql_session_rollback(engine):
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    sql_session = SqlSession(session_maker)

    await sql_session.begin()
    await sql_session.rollback()
    await sql_session.close()

    assert sql_session._session is None
