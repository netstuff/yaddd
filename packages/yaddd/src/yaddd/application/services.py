"""Application services."""

from abc import ABC, abstractmethod

from yaddd.application.commands import Command


__all__ = ["ApplicationService"]


class ApplicationService[C: Command, R](ABC):
    """Use-case coordinator.

    Loads aggregates through repository ports, invokes domain methods, saves,
    and publishes events after commit. May delegate steps to handlers.
    Dependencies are passed through the constructor — explicit DI without a
    container.
    """

    async def __call__(self, command: C) -> R:
        return await self.execute(command)

    @abstractmethod
    async def execute(self, command: C) -> R:
        """Run the use case for the given command."""
