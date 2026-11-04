"""Flat, serializable objects crossing the application boundary.

A DTO never references a domain object: only primitives and identifiers.
"""

from datetime import datetime
from uuid import UUID

from yaddd import DTO


__all__ = ["OrderDTO", "OrderPayloadKey", "OrderPlacement", "OrderPlacementKey"]


class OrderPayloadKey:
    """Keys of an order payload exposed to transport layers."""

    ORDER_ID = "order_id"
    REFERENCE = "reference"
    TOTAL = "total"
    STATUS = "status"


class OrderPlacementKey:
    """Keys of an order placement projection payload."""

    ORDER_ID = "order_id"
    REFERENCE = "reference"
    TOTAL = "total"
    PLACED_AT = "placed_at"


class OrderDTO(DTO):
    """Current state of an order as seen by transport layers."""

    order_id: UUID
    reference: str
    total: int
    status: str


class OrderPlacement(DTO):
    """Projection row written once, when an order is placed."""

    order_id: UUID
    reference: str
    total: int
    placed_at: datetime
