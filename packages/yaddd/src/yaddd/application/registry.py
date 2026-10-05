"""Handler registration decorators.

Handlers can be registered as classes or as plain functions:

    @command_handler(PlaceOrder)
    class PlaceOrderHandler(CommandHandler[PlaceOrder, UUID]):
        def __init__(self, uow: OrderUnitOfWork, publisher: EventPublisher) -> None:
            ...

    @command_handler(PlaceOrder)
    async def place_order(
        command: PlaceOrder,
        uow: OrderUnitOfWork,
        publisher: EventPublisher,
    ) -> UUID:
        ...

Both forms are stored in the module-level registry; the composition root is
responsible for building the actual callable that the bus will invoke.
"""

from collections.abc import Callable
from typing import Any, TypeVar

from yaddd.application.commands import Command, Query


_C = TypeVar("_C", bound=Command)
_Q = TypeVar("_Q", bound=Query)
_R = TypeVar("_R")

Handler = Callable[..., Any] | type[Any]


class HandlerRegistry:
    """Collects command/query handlers registered via decorators."""

    def __init__(self) -> None:
        self._commands: dict[type[Command], Handler] = {}
        self._queries: dict[type[Query], Handler] = {}

    def command_handler(
        self,
        command_type: type[_C],
    ) -> Callable[[Handler], Handler]:
        """Decorator that registers a class or function as a command handler."""

        def decorator(handler: Handler) -> Handler:
            self._commands[command_type] = handler
            return handler

        return decorator

    def query_handler(
        self,
        query_type: type[_Q],
    ) -> Callable[[Handler], Handler]:
        """Decorator that registers a class or function as a query handler."""

        def decorator(handler: Handler) -> Handler:
            self._queries[query_type] = handler
            return handler

        return decorator

    @property
    def commands(self) -> dict[type[Command], Handler]:
        """Registered command handlers keyed by command type."""
        return self._commands.copy()

    @property
    def queries(self) -> dict[type[Query], Handler]:
        """Registered query handlers keyed by query type."""
        return self._queries.copy()


# Module-level registry used by the decorators.  This is intentional global
# state for handler discovery: it is populated at import time and read once
# during application startup.
registry = HandlerRegistry()
command_handler = registry.command_handler
query_handler = registry.query_handler
