"""Aggregate root incapsulates domain entities."""

from abc import ABC
from typing import ClassVar, Sequence, TypeAlias

from yaddd.domain.rules import BusinessRule

from .base import AggregateMeta, EntityBase


RootInvariants: TypeAlias = Sequence[BusinessRule]


class AggregateRoot(EntityBase, meta=AggregateMeta):
    """Aggregate root."""

    INVARIANTS: ClassVar[RootInvariants] = ()

    def __check_invariants(self) -> bool:
        """Run invariants check."""
        for rule in self.INVARIANTS:
            if not rule.is_satisfied_by(self):
                raise ValueError(f"Invariant {x} is not passed!")  # TODO: add custom exception.

    def __post_init__(self):
        """Activate required aggregate features."""
        self.__check_invariants()


class invariants:
    """Class-decorator to define permanent and consistent invariants for aggregate root."""

    def __init__(self, klass):
        if not isssubclass(klass, AggregateRoot):
            raise ValueError()  # TODO: add custom exception.

        self.klass = klass

    def __call__(self, invariants: RootInvariants):
        self.klass.INVARIANTS = invariants
