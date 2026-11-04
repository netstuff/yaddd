"""Shared vocabulary of the orders slice."""

from enum import StrEnum


__all__ = ["OrderErrorMessage", "OrderField", "OrderStatus"]


class OrderStatus(StrEnum):
    """Lifecycle states of an order."""

    NEW = "new"
    PLACED = "placed"
    PAID = "paid"


class OrderField:
    """Names of aggregate fields used across the slice."""

    ID = "id"
    REFERENCE = "reference"
    TOTAL = "total"
    STATUS = "status"
    CARD_TOKEN = "card_token"


class OrderErrorMessage:
    """Human-readable messages produced by order business rules."""

    TOTAL_MUST_BE_POSITIVE = "order total must be positive"
    ORDER_MUST_BE_PLACED = "only a placed order can be paid"
