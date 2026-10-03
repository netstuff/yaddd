"""Domain event publication."""

from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from yaddd.domain.events import DomainEvent


__all__ = ["EventHandler", "EventPublisher", "InMemoryEventPublisher"]

type EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventPublisher(Protocol):
    """The only sanctioned publication point for domain events.

    Handlers and application services publish events pulled from aggregates
    (``AggregateRoot.pull_events()``) after a successful ``commit()``, so an
    event never leaves the system before the state is persisted.
    """

    async def publish(self, events: Sequence[DomainEvent]) -> None: ...


class InMemoryEventPublisher:
    """In-process publisher dispatching events to subscribed handlers.

    Handlers are invoked sequentially in subscription order. A handler
    subscribed to a base event type (e.g. ``DomainEvent`` itself) receives
    every event of its subtypes. A failing handler propagates the exception,
    interrupting the remaining dispatch.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Subscribe a handler to an event type (subtypes included)."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            for event_type, handlers in self._handlers.items():
                if isinstance(event, event_type):
                    for handler in handlers:
                        await handler(event)
