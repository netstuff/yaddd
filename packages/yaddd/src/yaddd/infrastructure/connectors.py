"""Connectors to external data sources."""

from typing import Any, Protocol


__all__ = ["Connector"]


class Connector(Protocol):
    """Abstraction over a data source: a DB session, an HTTP client, etc."""

    session: Any
