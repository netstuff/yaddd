"""Connectors to external data sources."""

from abc import ABC
from typing import Final

from yaddd.settings.http import HttpConnectorSettings


class ConnectorBase(ABC):
    """Data connector base."""
    ...


class HttpConnector(ConnectorBase, ABC):
    """Http connector."""

    def __init__(self, config: HttpConnectorSettings, **kwargs):
        self.config: Final[HttpConnectorSettings] = config
