"""GraphQL entrypoint port."""

from typing import Any, Protocol


__all__ = ["Resolver"]


class Resolver(Protocol):
    """GraphQL field resolver delegating to the application layer.

    Binding to strawberry/ariadne happens on the application side; the core
    defines only the port. ``root`` and ``info`` stay untyped on purpose —
    they belong to the concrete GraphQL framework.
    """

    async def resolve(self, root: Any, info: Any, **args: Any) -> Any: ...
