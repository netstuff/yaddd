"""Specification pattern with logical combinators.

The pattern encapsulates logical rules which can be composed by applying
logical operators: ``&`` (and), ``|`` (or), ``~`` (not), ``^`` (xor).

Read more at: https://martinfowler.com/apsupp/spec.pdf
"""

from __future__ import annotations

from abc import ABC, abstractmethod


__all__ = ["Specification"]


class Specification[C](ABC):
    """Reusable, composable condition over a candidate of type ``C``."""

    @abstractmethod
    def is_satisfied_by(self, candidate: C) -> bool:
        """Return True if the candidate satisfies the specification."""

    def __and__(self, other: Specification[C]) -> Specification[C]:
        return _AndSpecification(self, other)

    def __or__(self, other: Specification[C]) -> Specification[C]:
        return _OrSpecification(self, other)

    def __invert__(self) -> Specification[C]:
        return _NotSpecification(self)

    def __xor__(self, other: Specification[C]) -> Specification[C]:
        return _XorSpecification(self, other)


class _AndSpecification[C](Specification[C]):
    """Satisfied if all given specifications are satisfied."""

    def __init__(self, *specifications: Specification[C]) -> None:
        self._specifications = specifications

    def __and__(self, other: Specification[C]) -> Specification[C]:
        if isinstance(other, _AndSpecification):
            return _AndSpecification(*self._specifications, *other._specifications)
        return _AndSpecification(*self._specifications, other)

    def is_satisfied_by(self, candidate: C) -> bool:
        return all(spec.is_satisfied_by(candidate) for spec in self._specifications)


class _OrSpecification[C](Specification[C]):
    """Satisfied if any given specification is satisfied."""

    def __init__(self, *specifications: Specification[C]) -> None:
        self._specifications = specifications

    def __or__(self, other: Specification[C]) -> Specification[C]:
        if isinstance(other, _OrSpecification):
            return _OrSpecification(*self._specifications, *other._specifications)
        return _OrSpecification(*self._specifications, other)

    def is_satisfied_by(self, candidate: C) -> bool:
        return any(spec.is_satisfied_by(candidate) for spec in self._specifications)


class _NotSpecification[C](Specification[C]):
    """Satisfied if the given specification is NOT satisfied."""

    def __init__(self, specification: Specification[C]) -> None:
        self._specification = specification

    def is_satisfied_by(self, candidate: C) -> bool:
        return not self._specification.is_satisfied_by(candidate)


class _XorSpecification[C](Specification[C]):
    """Satisfied if exactly one of the two specifications is satisfied."""

    def __init__(self, left: Specification[C], right: Specification[C]) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: C) -> bool:
        return self._left.is_satisfied_by(candidate) ^ self._right.is_satisfied_by(candidate)
