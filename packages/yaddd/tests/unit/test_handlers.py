from uuid import UUID, uuid4

from yaddd.application import CommandHandler, Query, QueryHandler
from yaddd.application.commands import Command


class PlaceOrder(Command):
    order_id: UUID


class GetOrder(Query):
    order_id: UUID


class PlaceOrderHandler:
    async def handle(self, command: PlaceOrder) -> UUID:
        return command.order_id


class GetOrderHandler:
    def __init__(self, storage: dict[UUID, str]) -> None:
        self._storage = storage

    async def handle(self, query: GetOrder) -> str | None:
        return self._storage.get(query.order_id)


async def test_command_handler_executes():
    handler: CommandHandler[PlaceOrder, UUID] = PlaceOrderHandler()
    order_id = uuid4()
    assert await handler.handle(PlaceOrder(order_id=order_id)) == order_id


async def test_query_handler_uses_constructor_dependencies():
    order_id = uuid4()
    handler: QueryHandler[GetOrder, str | None] = GetOrderHandler({order_id: "placed"})
    assert await handler.handle(GetOrder(order_id=order_id)) == "placed"
    assert await handler.handle(GetOrder(order_id=uuid4())) is None
