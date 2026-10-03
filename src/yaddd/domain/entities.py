"""Domain entities and aggregate roots."""

from dataclasses import asdict
from typing import Any, ClassVar, cast
from uuid import UUID

from yaddd.domain.events import DomainEvent
from yaddd.domain.rules import BusinessRule
from yaddd.exceptions import InvariantViolationError
from yaddd.shared.dataclasses import DataclassMixin


__all__ = ["AggregateRoot", "Entity", "PrimaryKey"]

type PrimaryKey = UUID | int | str


class Entity(DataclassMixin):
    """Domain entity: an object defined by identity, not by attributes.

    Equality and hashing are based on the primary key (``pk``) within the
    same class. Subclasses are automatically converted to dataclasses
    (``eq=False, kw_only=True``) on definition — declare fields as annotations:

    Example:
        class User(Entity):
            id: UUID
            name: str

    ``INVARIANTS`` holds self-consistency rules checked after construction;
    put aggregate-wide rules on the aggregate root instead.

    If a subclass defines its own ``__post_init__``, it must call
    ``super().__post_init__()`` to keep the invariant check.
    """

    PRIMARY_KEY_NAME: ClassVar[str] = "id"
    INVARIANTS: ClassVar[tuple[BusinessRule[Any], ...]] = ()

    def __post_init__(self) -> None:
        self.check_invariants()

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.pk == other.pk

    def __hash__(self) -> int:
        return hash(self.pk)

    @property
    def pk(self) -> PrimaryKey:
        """Primary key used for identity checks."""
        return cast("PrimaryKey", getattr(self, self.PRIMARY_KEY_NAME))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entity fields into a dict."""
        return asdict(cast(Any, self))

    def check_invariants(self) -> None:
        """Raise :class:`InvariantViolationError` if any invariant is violated."""
        for rule in self.INVARIANTS:
            if not rule.is_satisfied_by(self):
                raise InvariantViolationError(f"Invariant violated: {rule}")


class AggregateRoot(Entity):
    """Aggregate root: the single entry point to a cluster of entities.

    Guarantees its ``INVARIANTS`` after construction and collects domain
    events until they are pulled by the application layer.
    """

    def __post_init__(self) -> None:
        self._events: list[DomainEvent] = []
        super().__post_init__()

    def add_event(self, event: DomainEvent) -> None:
        """Record a domain event to be published after a successful commit."""
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        """Return the collected events and clear the list."""
        events = self._events.copy()
        self._events.clear()
        return events
