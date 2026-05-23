"""Module for classes implementing Specification pattern.

The pattern encapsulates logical rules which can be composited by applying logical
operators (And, Or, Not).

Read more at: https://martinfowler.com/apsupp/spec.pdf
"""
import abc
from abc import ABC
from typing import Generic, Self, TypeVar


Candidate = TypeVar("Candidate")


class Specification(ABC, Generic[Candidate]):
    """Basic interface for specification."""

    def __and__(self, other: Self) -> Self:
        return _AndSpecification(self, other)

    def __or__(self, other: Self) -> Self:
        return _OrSpecification(self, other)

    def __invert__(self) -> Self:
        return _NotSpecification(self)

    def __xor__(self, other: Self) -> Self:
        return _XorSpecification(self, other)

    @abc.abstractmethod
    def is_satisfied_by(self, candidate: Candidate) -> bool:
        """Checks if a candidate satisfy the specification."""


class _AndSpecification(Specification[Candidate]):
    """Logical `And` condition for multiple specifications."""

    specifications: tuple[Specification, ...]

    def __init__(self, *specifications: Specification):
        self.specifications = specifications

    def __and__(self, other: Specification) -> Specification:
        if isinstance(other, _AndSpecification):
            self.specifications += other.specifications
        else:
            self.specifications += (other, )
        return self

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        """Satisfied if all given specs are also satisfied."""
        return all(
            specification.is_satisfied_by(candidate)
            for specification in self.specifications
        )


class _OrSpecification(Specification[Candidate]):
    """Logical `Or` condition for multiple specifications."""

    specifications: tuple[Specification, ...]

    def __init__(self, *specifications: Specification[Candidate]):
        self.specifications = specifications

    def __or__(self, other: Specification[Candidate]) -> Specification[Candidate]:
        if isinstance(other, _OrSpecification):
            self.specifications += other.specifications
        else:
            self.specifications += (other, )
        return self

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        """Satisfied if any given spec is satisfied."""
        return any(
            specification.is_satisfied_by(candidate)
            for specification in self.specifications
        )


class _NotSpecification(Specification[Candidate]):
    """Negation of a specification."""

    def __init__(self, specification: Specification):
        self.specification = specification

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        """Satisfied of a given spec is NOT satisfied."""
        return not self.specification.is_satisfied_by(candidate)


class _XorSpecification(Specification[Candidate]):
    """Exclusive Or Specification."""

    def __init__(self, left: Specification[Candidate], right: Specification[Candidate]):
        self.right = right
        self.left = left

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        """Satisfied if only one of the passed specification is satisfied."""
        return (
            self.right.is_satisfied_by(candidate) ^
            self.left.is_satisfied_by(candidate)
        )
