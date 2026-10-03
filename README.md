# yaddd
Yet another DDD for Python

Framework-agnostic (in base) simple library which provides a base layers for building DDD applications:
- Domain layer (DomainServices, AggregateRoots, Entities, ValueObjects, DomainEvent, Factories, Specifications, Rules)
- Application layer (ApplicationServices, Commands, Handlers, DTO, Mappers)
- Infrastructure layer (Repositories, ReadModels)
- Presentation layer (CLI, HTTP, GraphQL)

## Terms and definitions
First, read [Domain Driven Thesaurus](SPEC.md#14-глоссарий-ddd-терминов)

## Installation
`uv sync` — the project is managed with [uv](https://docs.astral.sh/uv/).

Optional dependencies enable integration with third-party libraries:
1. `yaddd[sqlalchemy]` — supports type decorators in `ValueObject`

## Quickstart
One import line gives you the whole public surface:

```python
import asyncio
from uuid import UUID, uuid4

from yaddd import (
    AggregateRoot,
    BusinessRule,
    Command,
    DomainEvent,
    HttpRequest,
    HttpResponse,
    InMemoryCrudRepository,
    InMemoryEventPublisher,
)


# --- Domain ---

class _PositiveTotal(BusinessRule):
    message = "total must be positive"

    def is_satisfied_by(self, candidate):
        return candidate.total > 0


class OrderPlaced(DomainEvent):
    order_id: UUID


class Order(AggregateRoot):
    id: UUID
    total: int

    INVARIANTS = (_PositiveTotal(),)

    def place(self):
        self.add_event(OrderPlaced(order_id=self.pk))


# --- Application ---

class PlaceOrder(Command):
    total: int


class PlaceOrderHandler:
    def __init__(self, orders, publisher):
        self._orders = orders
        self._publisher = publisher

    async def handle(self, command: PlaceOrder) -> UUID:
        order = Order(id=uuid4(), total=command.total)
        order.place()
        await self._orders.create(order)
        await self._publisher.publish(order.pull_events())
        return order.pk


# --- Presentation ---

class PlaceOrderHttpHandler:
    def __init__(self, handler):
        self._handler = handler

    async def handle(self, request: HttpRequest) -> HttpResponse:
        command = PlaceOrder(total=int(request.body.decode()))
        order_id = await self._handler.handle(command)
        return HttpResponse(status=201, body=str(order_id).encode())


# --- Composition: the entrypoint owns the event loop ---

async def on_order_placed(event: DomainEvent) -> None:
    print(f"event published: {event}")


async def main():
    publisher = InMemoryEventPublisher()
    publisher.subscribe(OrderPlaced, on_order_placed)

    orders = InMemoryCrudRepository[Order]()
    http = PlaceOrderHttpHandler(PlaceOrderHandler(orders, publisher))

    response = await http.handle(HttpRequest(method="POST", path="/orders", body=b"100"))
    print(response.status, response.body.decode())


if __name__ == "__main__":
    asyncio.run(main())
```

With a real database, wrap the use case in a `UnitOfWork` and publish events
after `commit()` — see [SPEC.md](SPEC.md) for the layer contracts.

## Development
```bash
uv sync                     # installs all dependency groups
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pyright src
uv run pytest
```
