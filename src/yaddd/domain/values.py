"""Common domain Value-Objects."""

from typing import TypeVar
from uuid import UUID


PrimaryKey = TypeVar("PrimaryKey", UUID, int, str)
