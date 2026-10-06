"""Business rules of the orders slice.

Rules are specifications: reusable, composable with ``&``, ``|``, ``~`` and
``^``. ``INVARIANTS`` checks them after construction; ``rule.check(x)`` raises
``BusinessRuleViolationError`` at a transition.

Each rule declares the state it needs as a protocol instead of importing the
aggregate. That keeps the slice acyclic — ``aggregates`` imports ``rules``, never
the other way round — and states the dependency honestly: ``TotalMustBePositive``
needs a total, not an entire order.

Rule names are phrased in the imperative: they describe the constraint that
must hold, e.g. ``TotalMustBePositive`` or ``OrderMustBePlaced``.
"""

from typing import Protocol

from yaddd import BusinessRule

from app.domain.orders.constants import OrderErrorMessage, OrderStatus
from app.domain.orders.value_objects import Money


__all__ = ["OrderMustBePlaced", "OrderState", "TotalMustBePositive"]


class OrderState(Protocol):
    """The part of an order the rules of this slice depend on."""

    total: Money
    status: OrderStatus


class TotalMustBePositive(BusinessRule[OrderState]):
    """An order total must be greater than zero."""

    message = OrderErrorMessage.TOTAL_MUST_BE_POSITIVE

    def is_satisfied_by(self, candidate: OrderState) -> bool:
        return candidate.total.value > 0


class OrderMustBePlaced(BusinessRule[OrderState]):
    """An order must be placed before it can be paid."""

    message = OrderErrorMessage.ORDER_MUST_BE_PLACED

    def is_satisfied_by(self, candidate: OrderState) -> bool:
        return candidate.status == OrderStatus.PLACED
