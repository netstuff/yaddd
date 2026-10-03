"""Application handlers."""

from typing import Protocol

from yaddd.application.commands import Command, Query


__all__ = ["CommandHandler", "QueryHandler"]


class CommandHandler[C: Command, R](Protocol):
    """Executor of a single command (1:1).

    Dependencies (repository ports, unit of work, publisher) are passed
    through the constructor — explicit DI without a container.
    """

    async def handle(self, command: C) -> R: ...


class QueryHandler[Q: Query, R](Protocol):
    """Executor of a single query (1:1).

    Dependencies (read model repositories, connectors) are passed through
    the constructor — explicit DI without a container.
    """

    async def handle(self, query: Q) -> R: ...
