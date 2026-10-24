"""Declarative order scenarios.

Scenarios replace a single monolithic handler with a readable sequence of
steps. Each step receives the same mutable :class:`OrderScenarioState` and may
branch to another scenario. Dependencies arrive through the constructor — the
composition root wires repositories, the unit of work and notification ports.
"""

from dataclasses import dataclass
from uuid import uuid4

from yaddd import Scenario, step
from yaddd.application.handlers import Context, Skip

from app.application.commands import PlaceOrder
from app.application.dto import OrderDTO
from app.application.mappers import Mapper
from app.application.notifications import NotificationSender
from app.application.uow import OrderUnitOfWork
from app.domain.orders.aggregates.order import Order
from app.domain.orders.value_objects import CardToken, Money, OrderReference


__all__ = [
    "MINIMUM_DISCOUNT_TOTAL",
    "DISCOUNT_RATE",
    "ApplyDiscountAction",
    "AmendOrderScenario",
    "NotifyCustomerScenario",
    "OrderScenarioState",
    "PlaceOrderResult",
    "PlaceOrderScenario",
    "apply_discount_step",
]


MINIMUM_DISCOUNT_TOTAL = 10000
DISCOUNT_RATE = 0.9


@dataclass(kw_only=True, slots=True)
class OrderScenarioState:
    """Mutable state carried through the place-order scenario.

    The state deliberately mixes the incoming command, the domain aggregate
    under construction and cross-cutting flags such as ``charged``. It is *not*
    a domain object: it is an execution scratchpad owned by the scenario runner.
    """

    command: PlaceOrder
    notifier: NotificationSender
    order: Order | None = None
    charged: bool = False
    notification_sent: bool = False


type PlaceOrderResult = OrderDTO


def _should_apply_discount(context: Context[OrderScenarioState]) -> bool:
    order = context.state.order
    if order is None:
        return False
    return order.total.value >= MINIMUM_DISCOUNT_TOTAL


def _has_card_token(context: Context[OrderScenarioState]) -> bool:
    return context.state.command.card_token is not None


def _notify_factory(context: Context[OrderScenarioState]) -> "NotifyCustomerScenario":
    return NotifyCustomerScenario(
        order=context.state.order,
        notifier=context.state.notifier,
    )


class ApplyDiscountAction:
    """Encapsulated step logic: apply a discount when the total is high enough.

    Keeping the action in a standalone callable makes it reusable across
    scenarios. The orchestration (when to run it) is declared by the scenario;
    the business rule lives here.
    """

    async def __call__(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
        order = context.state.order
        if order is None:
            return context.state
        discounted_total = int(order.total.value * DISCOUNT_RATE)
        context.state.order = Order(
            id=order.id,
            reference=order.reference,
            total=Money(discounted_total),
            status=order.status,
            card_token=order.card_token,
        )
        return context.state


apply_discount_step = step(
    ApplyDiscountAction(),
    name="apply_discount",
    when=_should_apply_discount,
)


class PlaceOrderScenario(Scenario[OrderScenarioState]):
    """Place an order as a sequence of discrete, traceable steps."""

    def __init__(self, uow: OrderUnitOfWork, mapper: Mapper[OrderDTO, Order]) -> None:
        self._uow = uow
        self._mapper = mapper

    @step
    async def build_order(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
        """Create the aggregate from the command, without accepting it yet."""
        command = context.state.command
        context.state.order = Order(
            id=uuid4(),
            reference=OrderReference(command.reference),
            total=Money(command.total),
            card_token=CardToken(command.card_token) if command.card_token is not None else None,
        )
        return context.state

    apply_discount = apply_discount_step

    @step(name="charge_payment", when=_has_card_token)
    async def charge_payment(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
        """Record that payment was collected for orders carrying a card token."""
        context.state.charged = True
        return context.state

    @step
    async def place_order(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
        """Accept the order and emit ``OrderPlaced``."""
        order = context.state.order
        if order is None:
            return context.state
        order.place()
        return context.state

    @step
    async def persist_order(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
        """Save the aggregate and let the unit of work publish its events."""
        order = context.state.order
        if order is None:
            return context.state
        async with self._uow:
            await self._uow.repos.orders.create(order)
            await self._uow.commit()
        return context.state

    @step(branch_to=_notify_factory)
    async def send_confirmation(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
        """Hand control to the notification scenario after persistence."""
        return context.state


class AmendOrderScenario(Scenario[OrderScenarioState]):
    """Re-apply discount rules to an already built order.

    Demonstrates that ``ApplyDiscountAction`` is not tied to the place-order
    flow: the same callable step can be reused in any scenario that works with
    the same context state.
    """

    apply_discount = apply_discount_step


class NotifyCustomerScenario(Scenario[OrderScenarioState]):
    """Post-purchase notification scenario, branched from ``PlaceOrderScenario``."""

    def __init__(self, order: Order | None, notifier: NotificationSender) -> None:
        self._order = order
        self._notifier = notifier

    @step
    async def send_notification(self, context: Context[OrderScenarioState]) -> OrderScenarioState | Skip:
        """Notify the customer that the order was placed.

        Tiny orders (total below the notification threshold) skip notification
        dynamically from inside the step. ``Skip`` is the imperative equivalent
        of ``@step(when=...)`` for decisions that need intermediate state.
        """
        if self._order is None:
            return Skip()
        if self._order.total.value < 100:
            return Skip()
        await self._notifier.send(
            event_type="OrderPlaced",
            payload={
                "order_id": str(self._order.id),
                "reference": self._order.reference.value,
                "total": self._order.total.value,
            },
        )
        context.state.notification_sent = True
        return context.state
