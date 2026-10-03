"""Base value object."""

import copy
from abc import ABC, abstractmethod
from typing import Any, Self, cast

from yaddd.exceptions import SensitiveValueAccessError


__all__ = ["SensitiveValueAccessError", "SensitiveValueObject", "ValueObject"]


class ValueObject[V](ABC):
    """Object of domain value.

    The core idea is to validate value on VO initialization, then trust VO data as validated.

    Example:
        class Name(ValueObject[str]):
            @classmethod
            def validate(cls, value: str) -> str:
                return value.strip()
    """

    _validated_value: V

    __slots__ = ("_validated_value",)

    def __init__(self, raw_value: V) -> None:
        """Validate the raw value and store the trusted result."""
        self._validated_value = self.validate(raw_value)

    def __eq__(self, other: Any) -> bool:
        return self.__class__ is other.__class__ and self._validated_value == other.value

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Self) -> bool:
        self._ensure_same_class(other)
        return bool(cast(Any, self._validated_value) < other._validated_value)

    def __le__(self, other: Self) -> bool:
        self._ensure_same_class(other)
        return bool(cast(Any, self._validated_value) <= other._validated_value)

    def __gt__(self, other: Self) -> bool:
        self._ensure_same_class(other)
        return bool(cast(Any, self._validated_value) > other._validated_value)

    def __ge__(self, other: Self) -> bool:
        self._ensure_same_class(other)
        return bool(cast(Any, self._validated_value) >= other._validated_value)

    def __bool__(self) -> bool:
        return bool(self._validated_value)

    def __repr__(self) -> str:
        return self.__class__.__name__ + f"('{self._validated_value}')"

    def __str__(self) -> str:
        return str(self._validated_value)

    def __hash__(self) -> int:
        return hash((id(self.__class__), self._validated_value))

    def __copy__(self) -> Self:
        return self.__class__(copy.copy(self._validated_value))

    def __deepcopy__(self, memo: dict[int, Any] | None) -> Self:
        return self.__class__(copy.deepcopy(self._validated_value, memo))

    @property
    def value(self) -> V:
        """Access to trusted value."""
        return self._validated_value

    @classmethod
    @abstractmethod
    def validate(cls, value: V) -> V:
        """Validate the raw value and return the trusted value."""

    def _ensure_same_class(self, other: Self) -> None:
        if self.__class__ is not other.__class__:
            raise TypeError(f"unsupported operand type(s) for operation: '{self.__class__}' and '{other.__class__}'")


class SensitiveValueObject[V](ValueObject[V]):
    """A value object whose payload must not leak into logs or representations.

    ``__repr__`` returns a masked value and ``__str__`` raises
    :class:`SensitiveValueAccessError`.

    Example:
        class Password(SensitiveValueObject[str]):
            @classmethod
            def validate(cls, value: str) -> str:
                if len(value) < 8:
                    raise ValidationError("password too short")
                return value
    """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}([MASKED])"

    def __str__(self) -> str:
        raise SensitiveValueAccessError(self.__class__.__name__)
