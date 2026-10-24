"""Use-case handlers of the orders slice.

A handler loads aggregates through repository ports, calls domain methods,
commits, and only then lets the unit of work publish the events collected on
those aggregates. Dependencies arrive through the constructor — explicit DI,
no container, no service locator.

``PlaceOrderHandler`` now delegates to a declarative :class:`Scenario` so the
workflow steps (build, optional discount, optional payment, place, persist,
notify) are visible as first-class methods instead of hiding inside one
monolithic ``execute`` body.
"""

from yaddd import ApplicationService, EntityNotFoundError, ScenarioRunner, command_handler

from app.application.commands import MarkOrderPaid, PlaceOrder
from app.application.dto import OrderDTO
from app.application.mappers import OrderMapper
from app.application.notifications import NotificationSender
from app.application.scenarios import OrderScenarioState, PlaceOrderScenario
from app.application.uow import OrderUnitOfWork
from app.domain.orders.aggregates.order import Order


__all__ = ["MarkOrderPaidHandler", "PlaceOrderHandler"]


@command_handler(PlaceOrder)
class PlaceOrderHandler(ApplicationService[PlaceOrder, OrderDTO]):
    """Creates an order, accepts it and publishes ``OrderPlaced`` on commit.

    The actual workflow lives in :class:`PlaceOrderScenario`; this handler is a
    thin adapter that turns a command into the scenario's initial state and
    runs it through a :class:`ScenarioRunner`.
    """

    def __init__(self, uow: OrderUnitOfWork, mapper: OrderMapper, notifier: NotificationSender) -> None:
        self._uow = uow
        self._mapper = mapper
        self._notifier = notifier

    async def execute(self, command: PlaceOrder) -> OrderDTO:
        runner = ScenarioRunner[OrderScenarioState]()
        state = OrderScenarioState(command=command, notifier=self._notifier)
        await runner.run([PlaceOrderScenario(self._uow, self._mapper)], initial_state=state)

        order = state.order
        if order is None:
            raise RuntimeError("PlaceOrderScenario finished without creating an order")

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
