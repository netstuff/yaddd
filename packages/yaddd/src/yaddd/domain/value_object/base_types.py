"""Concrete value object base types."""

from __future__ import annotations

import datetime
import operator
from abc import abstractmethod
from collections.abc import Callable, Hashable, ItemsView, Iterator, KeysView, ValuesView
from decimal import Decimal
from time import struct_time
from typing import Any, Literal, Never, Self, SupportsIndex, TypeGuard, cast, overload

from yaddd.domain.value_object.base import ValueObject
from yaddd.domain.value_object.registry import VOBaseTypesRegistry


__all__ = [
    "AnyDateValueObject",
    "AnyStrValueObject",
    "BytesValueObject",
    "DatetimeValueObject",
    "DateValueObject",
    "DecimalValueObject",
    "DictValueObject",
    "FloatValueObject",
    "IntValueObject",
    "NumericValueObject",
    "StringValueObject",
]


class NumericValueObject[N: (int, float, Decimal)](ValueObject[N]):
    """Value object wrapping a number."""

    def __add__(self, other: Self) -> Self:
        self._ensure_same_class(other)
        return self.__class__(self._validated_value + other._validated_value)

    def __sub__(self, other: Self) -> Self:
        self._ensure_same_class(other)
        return self.__class__(self._validated_value - other._validated_value)

    def __neg__(self) -> Self:
        return self.__class__(-self._validated_value)

    def __pos__(self) -> Self:
        return self.__class__(+self._validated_value)

    def __abs__(self) -> Self:
        return self.__class__(abs(cast(Any, self._validated_value)))

    @abstractmethod
    def __int__(self) -> int: ...

    @abstractmethod
    def __float__(self) -> float: ...

    @abstractmethod
    def __round__(self, ndigits: int | None = None) -> Self: ...


@VOBaseTypesRegistry.register
class IntValueObject(NumericValueObject[int]):
    """Value object wrapping an int."""

    def __int__(self) -> int:
        return self._validated_value

    def __float__(self) -> float:
        return float(self._validated_value)

    def __round__(self, ndigits: int | None = None) -> Self:
        return self


@VOBaseTypesRegistry.register
class FloatValueObject(NumericValueObject[float]):
    """Value object wrapping a float."""

    def __int__(self) -> int:
        return int(self._validated_value)

    def __float__(self) -> float:
        return self._validated_value

    def __round__(self, ndigits: int | None = None) -> Self:
        if ndigits is None:
            return self.__class__(round(self._validated_value))
        return self.__class__(round(self._validated_value, ndigits))


@VOBaseTypesRegistry.register
class DecimalValueObject(NumericValueObject[Decimal]):
    """Value object wrapping a Decimal."""

    def __int__(self) -> int:
        return int(self._validated_value)

    def __float__(self) -> float:
        return float(self._validated_value)

    def __round__(self, ndigits: int | None = None) -> Self:
        return self.__class__(self._validated_value.__round__(ndigits or 0))


class AnyStrValueObject[S: (str, bytes)](ValueObject[S]):
    """Value object wrapping a string-like value (str or bytes)."""

    @abstractmethod
    def __bytes__(self) -> bytes: ...

    def __add__(self, other: Self) -> Self:
        self._ensure_same_class(other)
        return self.__class__(self._validated_value + other._validated_value)

    def __len__(self) -> int:
        return len(self._validated_value)

    def __contains__(self, value: S | Self) -> bool:
        return operator.contains(self._validated_value, value)

    def __iter__(self) -> Iterator[str | int]:
        return iter(self._validated_value)

    def __getitem__(self, item: int) -> str | int:
        return self._validated_value[item]

    def startswith(
        self,
        prefix: S | tuple[S, ...],
        start: SupportsIndex | None = None,
        end: SupportsIndex | None = None,
    ) -> bool:
        return bool(cast(Any, self._validated_value).startswith(prefix, start, end))


@VOBaseTypesRegistry.register
class StringValueObject(AnyStrValueObject[str]):
    """Value object wrapping a str."""

    def __bytes__(self) -> bytes:
        return self._validated_value.encode()

    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        return self._validated_value.encode(encoding=encoding, errors=errors)


@VOBaseTypesRegistry.register
class BytesValueObject(AnyStrValueObject[bytes]):
    """Value object wrapping bytes."""

    def __bytes__(self) -> bytes:
        return self._validated_value

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        return self._validated_value.decode(encoding=encoding, errors=errors)


class AnyDateValueObject[D: (datetime.date, datetime.datetime)](ValueObject[D]):
    """Value object wrapping a date or datetime."""

    def __lt__(self, other: D | ValueObject[D]) -> bool:
        return self._compare(other, "__lt__")

    def __le__(self, other: D | ValueObject[D]) -> bool:
        return self._compare(other, "__le__")

    def __gt__(self, other: D | ValueObject[D]) -> bool:
        return self._compare(other, "__gt__")

    def __ge__(self, other: D | ValueObject[D]) -> bool:
        return self._compare(other, "__ge__")

    def __add__(self, other: datetime.timedelta) -> Self:
        self._ensure_timedelta(other)
        return self.__class__(self._validated_value + other)

    @overload
    def __sub__(self, other: AnyDateValueObject[D]) -> datetime.timedelta: ...

    @overload
    def __sub__(self, other: datetime.timedelta) -> Self: ...

    def __sub__(self, other: datetime.timedelta | AnyDateValueObject[D]) -> datetime.timedelta | Self:
        match other:
            case datetime.timedelta():
                return self.__class__(self._validated_value - other)
            case AnyDateValueObject():
                return self._validated_value - other._validated_value
            case _:
                self._raise_unsupported_exc(other)

    @property
    def year(self) -> int:
        return self._validated_value.year

    @property
    def month(self) -> int:
        return self._validated_value.month

    @property
    def day(self) -> int:
        return self._validated_value.day

    def timetuple(self) -> struct_time:
        return self._validated_value.timetuple()

    def toordinal(self) -> int:
        return self._validated_value.toordinal()

    def weekday(self) -> int:
        return self._validated_value.weekday()

    def isoweekday(self) -> int:
        return self._validated_value.isoweekday()

    def isocalendar(self) -> tuple[int, int, int]:
        return self._validated_value.isocalendar()

    def isoformat(self) -> str:
        return self._validated_value.isoformat()

    def ctime(self) -> str:
        return self._validated_value.ctime()

    def strftime(self, fmt: str) -> str:
        return self._validated_value.strftime(fmt)

    def replace(self, *args: Any, **kwargs: Any) -> Self:
        return self.__class__(self._validated_value.replace(*args, **kwargs))

    def _ensure_timedelta(self, other: Any) -> None:
        if not isinstance(other, datetime.timedelta):
            self._raise_unsupported_exc(other)

    def _raise_unsupported_exc(self, other: Any) -> Never:
        raise TypeError(f"unsupported operand type(s) for operation: '{self.__class__}' and '{other.__class__}'")

    def _compare(
        self,
        other: D | ValueObject[D],
        method: Literal["__lt__", "__le__", "__gt__", "__ge__"],
    ) -> bool:
        comparison_function: Callable[[D | datetime.date], bool] = getattr(self._validated_value, method)
        match other:
            case datetime.date():
                return comparison_function(other)
            case AnyDateValueObject():
                return comparison_function(other._validated_value)
            case _:
                self._raise_unsupported_exc(other)


@VOBaseTypesRegistry.register
class DateValueObject(AnyDateValueObject[datetime.date]):
    """Value object wrapping a date."""


@VOBaseTypesRegistry.register
class DatetimeValueObject(AnyDateValueObject[datetime.datetime]):
    """Value object wrapping a datetime."""

    @property
    def hour(self) -> int:
        return self._validated_value.hour

    @property
    def minute(self) -> int:
        return self._validated_value.minute

    @property
    def second(self) -> int:
        return self._validated_value.second

    @property
    def microsecond(self) -> int:
        return self._validated_value.microsecond

    @property
    def tzinfo(self) -> datetime.tzinfo | None:
        return self._validated_value.tzinfo

    @property
    def fold(self) -> int:
        return self._validated_value.fold

    def date(self) -> datetime.date:
        return self._validated_value.date()

    def timestamp(self) -> float:
        return self._validated_value.timestamp()

    def utcoffset(self) -> datetime.timedelta | None:
        return self._validated_value.utcoffset()

    def tzname(self) -> str | None:
        return self._validated_value.tzname()

    def dst(self) -> datetime.timedelta | None:
        return self._validated_value.dst()

    def astimezone(self, tz: datetime.tzinfo | None = None) -> datetime.datetime:
        return self._validated_value.astimezone(tz=tz)


@VOBaseTypesRegistry.register
class DictValueObject[K: Hashable, V](ValueObject[dict[K, V]]):
    """Value object wrapping a dict."""

    def __iter__(self) -> Iterator[K]:
        return iter(self._validated_value)

    def __len__(self) -> int:
        return len(self._validated_value)

    def __getitem__(self, key: K) -> V:
        return self._validated_value[key]

    def get[T](self, key: K, default: V | T | None = None) -> V | T | None:
        return self._validated_value.get(key, default)

    def items(self) -> ItemsView[K, V]:
        return self._validated_value.items()

    def keys(self) -> KeysView[K]:
        return self._validated_value.keys()

    def values(self) -> ValuesView[V]:
        return self._validated_value.values()

    def __contains__(self, item: object) -> TypeGuard[K]:
        return item in self._validated_value
