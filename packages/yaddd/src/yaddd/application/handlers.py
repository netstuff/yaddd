"""Application handlers."""

from typing import Protocol

from yaddd.application.commands import Command, Query


__all__ = ["CommandHandler", "MessageHandler", "QueryHandler"]


class MessageHandler[M, R](Protocol):
    """Executor of a single message (1:1).

    Dependencies (repository ports, unit of work, publisher) are passed
    through the constructor — explicit DI without a container.
    """

    async def handle(self, message: M) -> R: ...


class CommandHandler[C: Command, R](MessageHandler[C, R], Protocol):
    """Executor of a single command (1:1)."""


class QueryHandler[Q: Query, R](MessageHandler[Q, R], Protocol):
    """Executor of a single query (1:1)."""
