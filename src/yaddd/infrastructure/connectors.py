"""Connectors to external data sources."""

from abc import ABC
from typing import Any, Final, Protocol

from yaddd.settings.http import HttpConnectorSettings


class ConnectorBase(Protocol):
    """Data connector base."""

    session: Any


class HttpConnector(ConnectorBase, ABC):
    """Http connector."""

    def __init__(self, config: HttpConnectorSettings, **kwargs):
        self.config: Final[HttpConnectorSettings] = config
