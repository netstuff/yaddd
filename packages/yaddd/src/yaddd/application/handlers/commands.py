"""Command handler protocol."""

from typing import Protocol

from yaddd.application.commands import Command
from yaddd.application.handlers.messages import MessageHandler


__all__ = ["CommandHandler"]


class CommandHandler[C: Command, R](MessageHandler[C, R], Protocol):
    """Executor of a single command (1:1)."""
