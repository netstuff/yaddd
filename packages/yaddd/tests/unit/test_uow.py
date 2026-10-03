from types import TracebackType
from typing import Self

from yaddd.application import UnitOfWork


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.exited = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.exited = True
        if exc_type is not None and not self.committed:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


async def test_uow_commits_explicitly():
    uow: UnitOfWork = FakeUnitOfWork()
    async with uow:
        await uow.commit()

    assert uow.committed
    assert uow.exited


async def test_uow_rolls_back_on_exception():
    uow = FakeUnitOfWork()
    try:
        async with uow:
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert not uow.committed
    assert uow.rolled_back
