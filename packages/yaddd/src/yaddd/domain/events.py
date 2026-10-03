"""Domain events."""

from dataclasses import field
from datetime import UTC, datetime

from yaddd.shared.dataclasses import FrozenDataclassMixin


__all__ = ["DomainEvent"]


class DomainEvent(FrozenDataclassMixin):
    """Immutable record of a fact that happened in the domain.

    The event name is the class name. Subclasses are automatically converted
    to frozen dataclasses (``frozen=True, kw_only=True``); declare the payload
    as annotations:

    Example:
        class OrderPlaced(DomainEvent):
            order_id: UUID
            total: int
    """

    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
