"""Query handler protocol."""

from typing import Protocol

from yaddd.application.commands import Query
from yaddd.application.handlers.messages import MessageHandler


__all__ = ["QueryHandler"]


class QueryHandler[Q: Query, R](MessageHandler[Q, R], Protocol):
    """Executor of a single query (1:1)."""
