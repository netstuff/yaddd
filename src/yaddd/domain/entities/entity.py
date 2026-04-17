"""Domain entities locating around an aggregate root."""

from abc import ABC

from .base import AggregateMeta, EntityBase


class Entity(EntityBase, meta=AggregateMeta):
    """Domain entity."""
