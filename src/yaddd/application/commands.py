"""Application commands."""

from typing import Protocol

# TODO: перейти с protocol на нативный dataclass.

class Command(Protocol):
    """Application command base."""
    ...
