"""Reusable contract-test suites for port implementations.

Test-only module: importing it pulls in ``pytest``, so it is meant to be
imported solely from the test suites of ``yaddd`` and its plugins. It is
deliberately not re-exported from the top-level ``yaddd`` package.

Usage — subclass a contract in your plugin's test suite and override the
fixtures::

    class TestMyRepository(CrudRepositoryContract):
        @pytest.fixture
        def repo(self) -> CrudRepository[Any]:
            return MyRepository(...)

        @pytest.fixture
        def aggregate_factory(self) -> Callable[[], AggregateRoot]:
            return lambda: MyAggregate(id=uuid4().hex, label=uuid4().hex[:8])

Contract classes are collected by pytest only through subclasses (their names
do not start with ``Test``).
"""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from yaddd.application.uow import UnitOfWork
from yaddd.domain.entities import AggregateRoot
from yaddd.domain.repositories import CrudRepository
from yaddd.exceptions import EntityNotFoundError


__all__ = ["CrudRepositoryContract", "UnitOfWorkContract"]


class CrudRepositoryContract:
    """Executable specification of the ``CrudRepository`` port.

    Subclass in a plugin's test suite and override the two fixtures:

    - ``repo`` — a fresh, empty repository per test;
    - ``aggregate_factory`` — a callable producing UNIQUE aggregates on every
      call. Uniqueness must extend beyond the primary key to at least one
      regular field (e.g. derive a field from ``uuid4``), so that the
      ``update`` test can prove that stored state was really replaced.
      The aggregate must have at least one non-pk field, stored raw (the same
      value the aggregate exposes via ``to_dict()``), so equality filters
      match.
    """

    @pytest.fixture
    def repo(self) -> CrudRepository[Any]:
        """A fresh, empty repository under test."""
        raise NotImplementedError

    @pytest.fixture
    def aggregate_factory(self) -> Callable[[], AggregateRoot]:
        """Produce a new, unique aggregate on every call."""
        raise NotImplementedError

    async def test_create_then_get_returns_stored(
        self, repo: CrudRepository[Any], aggregate_factory: Callable[[], AggregateRoot]
    ) -> None:
        instance = await repo.create(aggregate_factory())

        stored = await repo.get(instance.pk)

        assert stored is not None
        assert stored.to_dict() == instance.to_dict()

    async def test_get_missing_returns_none(
        self, repo: CrudRepository[Any], aggregate_factory: Callable[[], AggregateRoot]
    ) -> None:
        assert await repo.get(aggregate_factory().pk) is None

    async def test_update_replaces_stored_state(
        self, repo: CrudRepository[Any], aggregate_factory: Callable[[], AggregateRoot]
    ) -> None:
        original = await repo.create(aggregate_factory())
        updated = aggregate_factory()
        setattr(updated, updated.PRIMARY_KEY_NAME, original.pk)

        await repo.update(updated)

        stored = await repo.get(original.pk)
        assert stored is not None
        assert stored.to_dict() == updated.to_dict()
        assert stored.to_dict() != original.to_dict()

    async def test_update_missing_raises_entity_not_found(
        self, repo: CrudRepository[Any], aggregate_factory: Callable[[], AggregateRoot]
    ) -> None:
        with pytest.raises(EntityNotFoundError):
            await repo.update(aggregate_factory())

    async def test_delete_then_get_returns_none(
        self, repo: CrudRepository[Any], aggregate_factory: Callable[[], AggregateRoot]
    ) -> None:
        instance = await repo.create(aggregate_factory())

        await repo.delete(instance.pk)

        assert await repo.get(instance.pk) is None

    async def test_delete_missing_is_idempotent(
        self, repo: CrudRepository[Any], aggregate_factory: Callable[[], AggregateRoot]
    ) -> None:
        await repo.delete(aggregate_factory().pk)

    async def test_read_with_equality_filter_returns_only_matches(
        self, repo: CrudRepository[Any], aggregate_factory: Callable[[], AggregateRoot]
    ) -> None:
        first = await repo.create(aggregate_factory())
        await repo.create(aggregate_factory())
        key, value = next((k, v) for k, v in first.to_dict().items() if k != first.PRIMARY_KEY_NAME)

        matches = await repo.read({key: value})

        assert matches
        assert all(item.to_dict()[key] == value for item in matches)

    async def test_read_slice_semantics(
        self, repo: CrudRepository[Any], aggregate_factory: Callable[[], AggregateRoot]
    ) -> None:
        for _ in range(3):
            await repo.create(aggregate_factory())

        assert len(await repo.read()) == 3  # default slice (0, 0) returns everything
        assert len(await repo.read(slice=(0, 0))) == 3  # limit=0 means no limit
        assert len(await repo.read(slice=(1, 1))) == 1  # single item from the offset
        assert len(await repo.read(slice=(2, 0))) == 1  # the rest starting from the offset


class UnitOfWorkContract:
    """Executable specification of the ``UnitOfWork`` port.

    Subclass in a plugin's test suite and override:

    - ``uow`` — a fresh unit of work per test;
    - ``assert_rolled_back`` (optional) — an async callable, invoked after an
      exception was raised inside the context, that asserts the
      implementation really discarded uncommitted work (e.g. via database
      state). Returns ``None`` by default: a bare ``UnitOfWork`` exposes no
      observable state, so the generic suite can only verify that exceptions
      propagate — proof of rollback is implementation-specific.
    """

    @pytest.fixture
    def uow(self) -> UnitOfWork:
        """A fresh unit of work under test."""
        raise NotImplementedError

    @pytest.fixture
    def assert_rolled_back(self) -> Callable[[], Awaitable[None]] | None:
        """Optional hook verifying rollback after an exceptional exit."""
        return None

    async def test_context_manager_enter_and_exit(self, uow: UnitOfWork) -> None:
        async with uow:
            pass

    async def test_commit_completes(self, uow: UnitOfWork) -> None:
        async with uow:
            await uow.commit()

    async def test_exception_inside_context_propagates(
        self, uow: UnitOfWork, assert_rolled_back: Callable[[], Awaitable[None]] | None
    ) -> None:
        with pytest.raises(RuntimeError, match="boom"):
            async with uow:
                raise RuntimeError("boom")

        if assert_rolled_back is not None:
            await assert_rolled_back()
