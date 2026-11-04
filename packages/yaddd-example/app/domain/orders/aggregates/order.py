"""The ``Order`` aggregate root — the single entry point into order state."""

from typing import ClassVar
from uuid import UUID

from yaddd import AggregateRoot

from app.domain.orders.constants import OrderStatus
from app.domain.orders.events import OrderPaid, OrderPlaced
from app.domain.orders.rules import OrderMustBePlaced, TotalMustBePositive
from app.domain.orders.value_objects import CardToken, Money, OrderReference


__all__ = ["Order"]


class Order(AggregateRoot):
    """An order with a reference, a total and a payment state.

    ``AggregateRoot`` turns this class into a keyword-only dataclass, so
    declare fields as annotations and pass them by name. ``INVARIANTS`` are
    re-checked on every construction.

    All state changes go through the methods below. Assigning to a field from
    the outside bypasses the invariants and the event stream, which is exactly
    what ``yaddd-linter`` rule ``YDDD001`` refuses to let you do.
    """

    INVARIANTS = (TotalMustBePositive(),)
    PLACED_ONLY: ClassVar[OrderMustBePlaced] = OrderMustBePlaced()

    id: UUID
    reference: OrderReference
    total: Money
    status: OrderStatus = OrderStatus.NEW
    card_token: CardToken | None = None

    def place(self) -> None:
        """Accept the order and emit ``OrderPlaced``."""
        self.status = OrderStatus.PLACED
        self.add_event(
            OrderPlaced(
                order_id=self.id,
                reference=self.reference.value,
                total=self.total.value,
            )
        )

    def mark_paid(self) -> None:
        """Settle a placed order and emit ``OrderPaid``.

        Raises:
            BusinessRuleViolationError: if the order was not placed yet.
        """
        self.PLACED_ONLY.check(self)
        self.status = OrderStatus.PAID
        self.add_event(OrderPaid(order_id=self.id))
