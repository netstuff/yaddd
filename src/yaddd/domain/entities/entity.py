"""Domain entities locating around an aggregate root."""

from dataclasses import dataclass, asdict
from typing import Any

from .base import AggregateMeta, EntityBase


@dataclass  # TODO: implement pre-defined dataclass (aka `@model_class`)
class Entity(EntityBase, metaclass=AggregateMeta):
    """Domain entity."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
