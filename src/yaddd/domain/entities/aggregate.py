"""Aggregate root incapsulates domain entities."""

from dataclasses import dataclass
from typing import ClassVar, Sequence, TypeAlias

from yaddd.domain.rules import BusinessRule

from .entity import AggregateMeta, Entity


RootInvariants: TypeAlias = Sequence[BusinessRule]


@dataclass  # TODO: implement pre-defined dataclass (aka `@model_class`)
class AggregateRoot(Entity, metaclass=AggregateMeta):
    """Aggregate root."""

    INVARIANTS: ClassVar[RootInvariants] = ()

    def __check_invariants(self) -> bool:
        """Run invariants check."""
        for rule in self.INVARIANTS:
            if not rule.is_satisfied_by(self):
                raise ValueError(f"Invariant {rule} is not passed!")  # TODO: add custom exception.

        return True

    def __post_init__(self):
        """Activate required aggregate features."""
        self.__check_invariants()


class invariants:
    """Class-decorator to define permanent and consistent invariants for aggregate root."""

    def __init__(self, klass):
        if not issubclass(klass, AggregateRoot):
            raise ValueError()  # TODO: add custom exception.

        self.klass = klass

    def __call__(self, invariants: RootInvariants):
        self.klass.INVARIANTS = invariants
