"""Read models."""

from yaddd.shared.dataclasses import FrozenDataclassMixin


__all__ = ["ReadModel"]


class ReadModel(FrozenDataclassMixin):
    """Denormalized, read-optimized projection.

    Read models bypass aggregates and carry no domain invariants. Subclasses
    are automatically converted to frozen dataclasses; declare fields as
    annotations.

    Example:
        class OrderSummary(ReadModel):
            order_id: str
            customer_name: str
            total: int
    """
