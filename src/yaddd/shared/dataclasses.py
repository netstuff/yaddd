"""Mixins turning subclasses into dataclasses automatically.

Used internally by domain and application base classes so users only declare
fields as annotations, without a ``@dataclass`` decorator. The
``@dataclass_transform`` markers (PEP 681) let type checkers understand the
synthesized ``__init__``.
"""

from dataclasses import dataclass
from typing import Any, dataclass_transform


__all__ = ["DataclassMixin", "FrozenDataclassMixin"]


class DataclassMixin:
    """Convert each subclass into a dataclass (``eq=False, kw_only=True``)."""

    @dataclass_transform(eq_default=False, kw_only_default=True)
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "__dataclass_params__" not in cls.__dict__:
            dataclass(eq=False, kw_only=True)(cls)


class FrozenDataclassMixin:
    """Convert each subclass into a frozen dataclass (``frozen=True, kw_only=True``)."""

    @dataclass_transform(frozen_default=True, kw_only_default=True)
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "__dataclass_params__" not in cls.__dict__:
            dataclass(frozen=True, kw_only=True)(cls)
