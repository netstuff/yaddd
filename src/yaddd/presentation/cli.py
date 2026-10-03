"""CLI entrypoint port."""

from collections.abc import Sequence
from typing import Protocol


__all__ = ["CliCommand"]


class CliCommand(Protocol):
    """CLI entrypoint: parse args, run a use case, return an exit code.

    Neutral to argparse/click/typer — the adapter of the chosen library
    delegates to this port. ``run`` is synchronous on purpose: the entrypoint
    owns the event loop (``asyncio.run(...)`` inside) when the use case needs
    async application services.
    """

    def run(self, args: Sequence[str]) -> int: ...
