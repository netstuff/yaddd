"""Write/read port for the order placement projection."""

from typing import Protocol
from uuid import UUID

from app.application.dto import OrderPlacement


__all__ = ["OrderPlacementRepository"]


class OrderPlacementRepository(Protocol):
    """Append-only store of placed orders, used by the reporting side."""

    async def add(self, placement: OrderPlacement) -> None:
        """Append a placement row."""
        ...

    async def find_one(self, order_id: UUID) -> OrderPlacement | None:
        """Return the placement of ``order_id``, if any."""
        ...
