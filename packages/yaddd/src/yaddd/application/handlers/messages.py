"""Base message handler protocol."""

from typing import Protocol


__all__ = ["MessageHandler"]


class MessageHandler[M, R](Protocol):
    """Executor of a single message (1:1).

    Dependencies (repository ports, unit of work, publisher) are passed
    through the constructor — explicit DI without a container.
    """

    async def handle(self, message: M) -> R: ...
