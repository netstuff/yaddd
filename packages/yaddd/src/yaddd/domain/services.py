"""Domain services."""

from typing import Protocol


__all__ = ["DomainService"]


class DomainService(Protocol):
    """Stateless domain operation that does not belong to a single aggregate.

    Contract:
    - stateless: no instance state between calls;
    - synchronous, no I/O: domain ports are injected via the constructor;
    - speaks the ubiquitous language; input and output are domain objects.
    """
