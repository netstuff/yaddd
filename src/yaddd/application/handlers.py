"""Application handlers."""

from abc import ABC, abstractmethod
from typing import Any

from yaddd.application.commands import Command


class Handler(ABC):
    """Base class for all application handlers."""

    def __init__(self, command: Command, **kwargs):
        self._command = command

    def __call__(self, *args, **kwargs) -> Any:
        return self.handle(*args, **kwargs)

    @abstractmethod
    def handle(self, *args, **kwargs) -> Any:
        ...
