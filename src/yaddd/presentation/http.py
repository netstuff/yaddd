"""HTTP entrypoint ports.

Framework-neutral request/response types and the handler port. Adapters to
FastAPI/aiohttp/etc. map framework types onto these ports and live outside
the core.
"""

from dataclasses import field
from typing import Protocol

from yaddd.shared.dataclasses import FrozenDataclassMixin


__all__ = ["HttpHandler", "HttpRequest", "HttpResponse"]


class HttpRequest(FrozenDataclassMixin):
    """Framework-neutral HTTP request."""

    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body: bytes = b""


class HttpResponse(FrozenDataclassMixin):
    """Framework-neutral HTTP response."""

    status: int
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body: bytes = b""


class HttpHandler(Protocol):
    """HTTP entrypoint: request -> use case -> response.

    Parses the input into a command/query, delegates to a handler of the
    application layer and maps the resulting DTO onto an ``HttpResponse``.
    No domain logic.
    """

    async def handle(self, request: HttpRequest) -> HttpResponse: ...
