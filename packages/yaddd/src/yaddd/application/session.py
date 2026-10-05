"""Protocol-agnostic transactional resource.

A ``Session`` represents a single transactional resource that can be
coordinated by a ``Transaction``. Concrete implementations cover SQL
databases, HTTP calls, message brokers, or any other resource that needs
commit/rollback semantics.
"""

from typing import Protocol


__all__ = ["Session"]


class Session(Protocol):
    """A transactional resource participating in a unit of work."""

    async def begin(self) -> None:
        """Begin the transactional context (open connection, acquire lock)."""
        ...

    async def commit(self) -> None:
        """Persist all changes made within the session."""
        ...

    async def rollback(self) -> None:
        """Discard all changes made within the session."""
        ...

    async def close(self) -> None:
        """Release the underlying resource."""
        ...
