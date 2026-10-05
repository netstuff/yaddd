"""In-process message bus."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from yaddd.application.commands import Command, Query
from yaddd.exceptions import ApplicationError, HandlerNotFoundError


__all__ = ["CommandBus", "MessageBus", "QueryBus"]

M = TypeVar("M")
R = TypeVar("R")

Handler = Callable[[M], Awaitable[R]]


class MessageBus[M, R]:
    """In-process dispatcher: exactly one handler per message type (1:1).

    Base class for :class:`CommandBus` and :class:`QueryBus`. Dispatch is by
    the exact message class; a missing or duplicated registration is a
    configuration error, reported eagerly.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[M], Handler[M, R]] = {}

    def register(self, message_type: type[M], handler: Handler[M, R]) -> None:
        """Bind a handler to a message type."""
        if message_type in self._handlers:
            raise ApplicationError(f"Handler already registered for {message_type.__name__}")
        self._handlers[message_type] = handler

    async def dispatch(self, message: M) -> R:
        """Dispatch the message to its registered handler."""
        handler = self._handlers.get(type(message))
        if handler is None:
            raise HandlerNotFoundError(f"No handler registered for {type(message).__name__}")
        return await handler(message)

    async def __call__(self, message: M) -> R:
        return await self.dispatch(message)


class CommandBus[C: Command, R](MessageBus[C, R]):
    """Message bus for commands."""


class QueryBus[Q: Query, R](MessageBus[Q, R]):
    """Message bus for queries."""
