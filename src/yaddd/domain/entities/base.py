"""Domain entites base."""
from abc import ABC, ABCMeta
from dataclasses import dataclass
from typing import Any, Callable, Final, Sequence

from yaddd.domain.values import PrimaryKey


class EntityMeta(ABCMeta):
    """Meta-class for domain entities."""

    DC_PARAMS: Final[dict[str, bool]] = dict(eq=False, kw_only=True, repr=False)

    def __new__(mcs, name, bases, namespace, **kwargs):
        """Convert class to a dataclass."""
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        cls._invariants: set[Callable] = set()

        return dataclass(**mcs.DC_PARAMS)(cls)


class AggregateMeta(EntityMeta):
    """Meta-class for domain aggreagate roots."""


class EntityBase(ABC):
    """Base for entities and aggregates."""

    PRIMARY_KEY_NAME: Final[str] = "id"

    def __eq__(self, other: Any) -> bool:
        """Equality check for domain logic."""
        return isinstance(other, self.__class__) and self.pk == other.pk

    def __hash__(self) -> int:
        return hash(self.pk)

    @property
    def pk(self) -> PrimaryKey:
        """Default primary key, used only for equality check for domain logic."""
        return getattr(self, self.PRIMARY_KEY_NAME)


def invariants(fn):
    """Decorator to place a class method to invariants."""
    def wrapper(instance, rules: Sequence[set | list | tuple]):
        instance._invariants |= rules
