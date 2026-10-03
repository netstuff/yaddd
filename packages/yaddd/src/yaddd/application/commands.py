"""Application commands and queries."""

from yaddd.shared.dataclasses import FrozenDataclassMixin


__all__ = ["Command", "Query"]


class Command(FrozenDataclassMixin):
    """Immutable intent to change the state of the system.

    Subclasses are automatically converted to frozen dataclasses; declare the
    payload as annotations. No logic, only data.

    Example:
        class PlaceOrder(Command):
            order_id: UUID
            total: int
    """


class Query(FrozenDataclassMixin):
    """Immutable intent to read the state of the system, without side effects.

    Subclasses are automatically converted to frozen dataclasses; declare the
    payload as annotations. No logic, only data.

    Example:
        class GetOrder(Query):
            order_id: UUID
    """
