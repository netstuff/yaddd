"""Commands of the orders slice — immutable intents, payload only."""

from uuid import UUID

from yaddd import Command


__all__ = ["MarkOrderPaid", "PlaceOrder"]


class PlaceOrder(Command):
    """Register a new order and accept it."""

    reference: str
    total: int
    card_token: str | None = None


class MarkOrderPaid(Command):
    """Settle an already placed order."""

    order_id: UUID
