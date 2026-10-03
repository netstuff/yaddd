"""Data transfer objects."""

from yaddd.shared.dataclasses import FrozenDataclassMixin


__all__ = ["DTO"]


class DTO(FrozenDataclassMixin):
    """Flat, serializable object crossing the application boundary.

    Subclasses are automatically converted to frozen dataclasses; declare the
    payload as annotations. A DTO never references domain objects.

    Example:
        class OrderDTO(DTO):
            order_id: str
            total: int
    """
