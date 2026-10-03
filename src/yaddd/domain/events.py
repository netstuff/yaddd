"""Domain events."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, dataclass_transform


__all__ = ["DomainEvent"]


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
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

    @dataclass_transform(frozen_default=True, kw_only_default=True)
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "__dataclass_params__" not in cls.__dict__:
            dataclass(frozen=True, kw_only=True)(cls)
