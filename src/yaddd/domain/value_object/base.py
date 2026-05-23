"""Base value object."""

import copy
from abc import ABCMeta, abstractmethod
from typing import Any, Generic, Self, TypeVar


ValidatedValue = TypeVar("ValidatedValue")


class SensitiveValueAccessError(Exception):
    """Sensitive value access error."""

    message = "Access to {} is not allowed."

    def __init__(self, vo_name: str, *args, **kwargs) -> None:
        message = self.message.format(vo_name)
        super().__init__(message, *args, **kwargs)


class _ValueObjectMeta(ABCMeta):
    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        sensitive: bool = False,
        **kwargs: Any,
    ) -> type["ValueObject"]:
        if sensitive:
            namespace["__repr__"] = mcls.sensitive_repr
            namespace["__str__"] = mcls.sensitive_str

        return super().__new__(mcls, name, bases, namespace, **kwargs)  # type: ignore[return-value]

    def sensitive_repr(self):
        """Mask sensitive data."""
        return self.__class__.__name__ + "([MASKED])"

    def sensitive_str(self):
        # Sensitive objects can't be stored in DB through SQL Alchemy (it uses __str__). Fixme
        raise SensitiveValueAccessError(self.__class__.__name__)


class ValueObject(Generic[ValidatedValue], metaclass=_ValueObjectMeta):
    """Object of domain value.

    The core idea is to validate value on VO initialization, then trust VO data as validated.

    Meta attributes:
        sensitive (bool): If True, __repr__ will return a masked value;
            it's used to mask the value in logs.


    Example:
        class _SimpleVO(ValueObject):
            @classmethod
            def validate(cls, value: Any) -> Any:
                return value
    """

    sensitive: bool = False
    _validated_value: ValidatedValue

    __slots__ = ("_validated_value",)

    def __init__(self, raw_value: ValidatedValue) -> None:
        """ValueObject constructor."""
        self._validated_value = self.validate(raw_value)

    def __eq__(self, other: Any) -> bool:
        return self.__class__ is other.__class__ and self._validated_value == other.value

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Self) -> Any:
        self._ensure_same_class(other)
        return self._validated_value < other._validated_value  # type: ignore[operator]

    def __le__(self, other: Self) -> Any:
        self._ensure_same_class(other)
        return self._validated_value <= other._validated_value  # type: ignore[operator]

    def __gt__(self, other: Self) -> Any:
        self._ensure_same_class(other)
        return self._validated_value > other._validated_value  # type: ignore[operator]

    def __ge__(self, other: Self) -> Any:
        self._ensure_same_class(other)
        return self._validated_value >= other._validated_value  # type: ignore[operator]

    def __bool__(self) -> bool:
        return bool(self._validated_value)

    def __and__(self, other: Any) -> Any:
        return self & other

    def __xor__(self, other: Any) -> Any:
        return self ^ other

    def __or__(self, other: Any) -> Any:
        return self | other

    def __rand__(self, other: Self) -> Any:
        return other & self

    def __rxor__(self, other: Self) -> Any:
        return other ^ self

    def __ror__(self, other: Self) -> Any:
        return other | self

    def __iand__(self, other: Any) -> Any:
        return self & other

    def __ixor__(self, other: Any) -> Any:
        return self ^ other

    def __ior__(self, other: Any) -> Any:
        return self | other

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
    def value(self) -> ValidatedValue:
        """Access to trusted value."""
        return self._validated_value

    @classmethod
    @abstractmethod
    def validate(cls, value: ValidatedValue) -> ValidatedValue:
        """Type defining special validation algorythm."""

    def _ensure_same_class(self, other: Self) -> None:
        if self.__class__ is other.__class__:
            return
        raise TypeError(f"unsupported operand type(s) for operation: '{self.__class__}' and '{other.__class__}'")
