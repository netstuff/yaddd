"""Domain events of the orders slice.

Events are facts, not commands: they are recorded on the aggregate and pulled
by the unit of work *after* a successful commit.
"""

from uuid import UUID

from yaddd import DomainEvent


__all__ = ["OrderPaid", "OrderPlaced"]


class OrderPlaced(DomainEvent):
    """An order was accepted and persisted."""

    order_id: UUID
    reference: str
    total: int


class OrderPaid(DomainEvent):
    """A placed order was settled."""

    order_id: UUID
