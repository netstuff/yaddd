"""Mappers between domain objects and DTOs."""

from typing import Protocol

from yaddd.domain.entities import AggregateRoot


__all__ = ["Mapper"]


class Mapper[D, T: AggregateRoot](Protocol):
    """Bidirectional conversion between an aggregate and its DTO."""

    def to_dto(self, domain: T) -> D: ...

    def to_domain(self, dto: D) -> T: ...
