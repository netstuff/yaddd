"""Use-case handlers of the orders slice.

A handler loads aggregates through repository ports, calls domain methods,
commits, and only then lets the unit of work publish the events collected on
those aggregates. Dependencies arrive through the constructor — explicit DI,
no container, no service locator.
"""

from uuid import uuid4

from yaddd import ApplicationService, EntityNotFoundError, command_handler

from app.application.commands import MarkOrderPaid, PlaceOrder
from app.application.dto import OrderDTO
from app.application.mappers import OrderMapper
from app.application.uow import OrderUnitOfWork
from app.domain.orders.aggregates.order import Order
from app.domain.orders.value_objects import CardToken, Money, OrderReference


__all__ = ["MarkOrderPaidHandler", "PlaceOrderHandler"]


@command_handler(PlaceOrder)
class PlaceOrderHandler(ApplicationService[PlaceOrder, OrderDTO]):
    """Creates an order, accepts it and publishes ``OrderPlaced`` on commit."""

    def __init__(self, uow: OrderUnitOfWork, mapper: OrderMapper) -> None:
        self._uow = uow
        self._mapper = mapper

    async def execute(self, command: PlaceOrder) -> OrderDTO:
        order = Order(
            id=uuid4(),
            reference=OrderReference(command.reference),
            total=Money(command.total),
            card_token=CardToken(command.card_token) if command.card_token is not None else None,
        )
        order.place()

        async with self._uow:
            await self._uow.repos.orders.create(order)
            await self._uow.commit()

        return self._mapper.to_dto(order)


@command_handler(MarkOrderPaid)
class MarkOrderPaidHandler(ApplicationService[MarkOrderPaid, OrderDTO]):
    """Settles a placed order and publishes ``OrderPaid`` on commit.

    Raises:
        EntityNotFoundError: if no order carries the requested identifier.
        BusinessRuleViolationError: if the order was never placed.
    """

    def __init__(self, uow: OrderUnitOfWork, mapper: OrderMapper) -> None:
        self._uow = uow
        self._mapper = mapper

    async def execute(self, command: MarkOrderPaid) -> OrderDTO:
        async with self._uow:
            order: Order | None = await self._uow.repos.orders.get(command.order_id)
            if order is None:
                raise EntityNotFoundError(f"Order({command.order_id})")

            order.mark_paid()
            await self._uow.repos.orders.update(order)
            await self._uow.commit()

        return self._mapper.to_dto(order)
