from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from yaddd.presentation import CliCommand, HttpHandler, HttpRequest, HttpResponse, Resolver


def test_http_request_defaults():
    request = HttpRequest(method="GET", path="/orders")
    assert request.headers == {}
    assert request.body == b""


def test_http_request_is_frozen_and_kw_only():
    request = HttpRequest(method="GET", path="/orders", headers={"Accept": "application/json"})
    with pytest.raises(FrozenInstanceError):
        request.method = "POST"  # type: ignore[misc]
    with pytest.raises(TypeError):
        HttpRequest("GET", "/orders")  # type: ignore[misc]


def test_http_response_defaults():
    response = HttpResponse(status=200)
    assert response.headers == {}
    assert response.body == b""


async def test_http_handler_port():
    class HealthHandler:
        async def handle(self, request: HttpRequest) -> HttpResponse:
            assert request.path == "/health"
            return HttpResponse(status=200, body=b'{"status": "ok"}')

    handler: HttpHandler = HealthHandler()
    response = await handler.handle(HttpRequest(method="GET", path="/health"))

    assert response.status == 200
    assert response.body == b'{"status": "ok"}'


def test_cli_command_port():
    class ListOrders:
        def run(self, args: list[str]) -> int:
            return 0 if "--all" in args else 1

    command: CliCommand = ListOrders()
    assert command.run(["--all"]) == 0
    assert command.run([]) == 1


async def test_resolver_port():
    class OrderResolver:
        async def resolve(self, root: Any, info: Any, **args: Any) -> dict[str, Any]:
            return {"order_id": args["order_id"]}

    resolver: Resolver = OrderResolver()
    result = await resolver.resolve(None, None, order_id="42")

    assert result == {"order_id": "42"}
