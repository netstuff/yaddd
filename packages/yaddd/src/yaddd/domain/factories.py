"""Aggregate factories."""

from typing import Protocol

from yaddd.domain.entities import AggregateRoot


__all__ = ["Factory"]


class Factory[In, T: AggregateRoot](Protocol):
    """Encapsulates complex construction of a new aggregate.

    Creation only: identity generation, value object assembly, creation-time
    rules and the "created" event (recorded via ``AggregateRoot.add_event``).
    Reconstitution from storage belongs to repositories and mappers.

    Factories are synchronous and do no I/O: when construction needs
    external data, inject a domain port through the constructor.
    """

    def create(self, data: In) -> T: ...
