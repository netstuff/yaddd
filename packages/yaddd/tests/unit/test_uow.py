from dataclasses import dataclass
from types import TracebackType
from typing import Self

from yaddd.application import UnitOfWork
from yaddd.domain import AggregateRoot


class FakeRepositoryBundle:
    pass


class FakeUnitOfWork:
    def __init__(self) -> None:
        self._repos = FakeRepositoryBundle()
        self._tracked: list[AggregateRoot] = []
        self.committed = False
        self.rolled_back = False
        self.exited = False

    @property
    def repos(self) -> FakeRepositoryBundle:
        return self._repos

    def track(self, aggregate: AggregateRoot) -> None:
        self._tracked.append(aggregate)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.exited = True
        if exc_type is not None or not self.committed:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@dataclass
class FakeAggregate(AggregateRoot):
    id: str


async def test_uow_exposes_repositories():
    uow: UnitOfWork[FakeRepositoryBundle] = FakeUnitOfWork()
    assert isinstance(uow.repos, FakeRepositoryBundle)


async def test_uow_tracks_aggregates():
    uow: UnitOfWork[FakeRepositoryBundle] = FakeUnitOfWork()
    aggregate = FakeAggregate(id="1")
    uow.track(aggregate)
    assert uow._tracked == [aggregate]


async def test_uow_commits_explicitly():
    uow: UnitOfWork[FakeRepositoryBundle] = FakeUnitOfWork()
    async with uow:
        await uow.commit()

    assert uow.committed
    assert uow.exited
    assert not uow.rolled_back


async def test_uow_rolls_back_on_exception():
    uow = FakeUnitOfWork()
    try:
        async with uow:
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert not uow.committed
    assert uow.rolled_back
    assert uow.exited


async def test_uow_rolls_back_without_explicit_commit():
    uow = FakeUnitOfWork()
    async with uow:
        pass

    assert not uow.committed
    assert uow.rolled_back
    assert uow.exited
