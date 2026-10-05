"""Protocol-agnostic transaction implementation."""

from typing import TypeVar

from yaddd.application.events import EventPublisher
from yaddd.application.session import Session
from yaddd.application.transaction import Transaction
from yaddd.domain.entities import AggregateRoot
from yaddd.domain.events import DomainEvent


__all__ = ["BaseTransaction", "MultiTransaction"]

S = TypeVar("S", bound=Session)
T = TypeVar("T", bound=Session)


class BaseTransaction[S: Session](Transaction):
    """Coordinates a single ``Session`` resource for a single use case.

    Call ``commit()`` to persist the work and publish events from tracked
    aggregates. Exiting the context without ``commit()`` — or with an
    exception — rolls back. The session is always closed on exit.
    """

    def __init__(self, session: S, publisher: EventPublisher) -> None:
        self._session = session
        self._publisher = publisher
        self._aggregates: list[AggregateRoot] = []
        self._committed = False

    @property
    def session(self) -> S:
        """The transactional resource managed by this transaction."""
        return self._session

    def track(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate whose events should be published on commit."""
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)

    async def commit(self) -> None:
        """Persist the work and publish events from tracked aggregates."""
        await self._session.commit()
        events = self._collect_events()
        await self._publisher.publish(events)
        self._aggregates.clear()
        self._committed = True

    async def rollback(self) -> None:
        """Discard all changes made within the transaction."""
        await self._session.rollback()

    async def __aenter__(self) -> "BaseTransaction[S]":
        await self._session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        try:
            if exc_type is not None or not self._committed:
                await self.rollback()
        finally:
            await self._session.close()

    def _collect_events(self) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for aggregate in self._aggregates:
            events.extend(aggregate.pull_events())
        return events


class MultiTransaction(Transaction):
    """Coordinates multiple ``Session`` resources for a single use case.

    Call ``commit()`` to persist the work and publish events from tracked
    aggregates. Exiting the context without ``commit()`` — or with an
    exception — rolls back. Sessions are always closed on exit.
    """

    def __init__(self, sessions: list[Session], publisher: EventPublisher) -> None:
        self._sessions = sessions
        self._publisher = publisher
        self._aggregates: list[AggregateRoot] = []
        self._committed = False

    def get_session(self, session_type: type[T]) -> T:
        """Return the first session of the requested concrete type."""
        for session in self._sessions:
            if isinstance(session, session_type):
                return session
        raise ValueError(f"No session of type {session_type.__name__}")

    def track(self, aggregate: AggregateRoot) -> None:
        """Register an aggregate whose events should be published on commit."""
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)

    async def commit(self) -> None:
        """Persist the work and publish events from tracked aggregates."""
        for session in self._sessions:
            await session.commit()
        events = self._collect_events()
        await self._publisher.publish(events)
        self._aggregates.clear()
        self._committed = True

    async def rollback(self) -> None:
        """Discard all changes made within the transaction."""
        for session in self._sessions:
            await session.rollback()

    async def __aenter__(self) -> "MultiTransaction":
        for session in self._sessions:
            await session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        try:
            if exc_type is not None or not self._committed:
                await self.rollback()
        finally:
            for session in self._sessions:
                await session.close()

    def _collect_events(self) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for aggregate in self._aggregates:
            events.extend(aggregate.pull_events())
        return events
