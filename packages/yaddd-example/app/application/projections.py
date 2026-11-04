"""Projections: the read side of the domain event stream.

A projection never touches aggregates — it consumes facts that already
happened and materialises them into a read model. That is why projections live
next to the handlers instead of in ``domain``: they have no invariants to
protect, only idempotency to guarantee.
"""

from uuid import UUID

from app.application.dto import OrderPlacement, OrderPlacementKey
from app.application.messaging import EventEnvelope
from app.application.read_models import OrderPlacementRepository
from app.domain.orders.events import OrderPlaced


__all__ = ["OrderPlacedProjector"]


class OrderPlacedProjector:
    """Records every placed order into the ``order_placements`` read model.

    Brokers deliver at least once, so the projector is idempotent: a redelivered
    ``OrderPlaced`` for an already projected order is a no-op instead of a
    duplicate-key error.
    """

    def __init__(self, placements: OrderPlacementRepository) -> None:
        self._placements = placements

    async def __call__(self, envelope: EventEnvelope) -> None:
        """Project one envelope, ignoring events of other slices."""
        if envelope.event_type != OrderPlaced.__name__:
            return

        payload = envelope.payload
        order_id = UUID(str(payload[OrderPlacementKey.ORDER_ID]))
        if await self._placements.find_one(order_id) is not None:
            return

        await self._placements.add(
            OrderPlacement(
                order_id=order_id,
                reference=str(payload[OrderPlacementKey.REFERENCE]),
                total=int(payload[OrderPlacementKey.TOTAL]),
                placed_at=envelope.occurred_at,
            )
        )
