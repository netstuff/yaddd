import datetime
import typing
from abc import ABC, abstractmethod
from decimal import Decimal
from time import struct_time
from typing import Never, Self, overload

from .base import ValueObject
from .registry import VOBaseTypesRegistry


AnyNumeric = typing.TypeVar("AnyNumeric", int, float, Decimal)


class NumericValueObject(ValueObject[AnyNumeric]):  # type: ignore[misc]
    _validated_value: AnyNumeric

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
        return self.__class__(abs(self._validated_value))

    @abstractmethod
    def __int__(self) -> int: ...

    @abstractmethod
    def __float__(self) -> float: ...

    @abstractmethod
    def __round__(self, ndigits: int | None = None) -> Self: ...


@VOBaseTypesRegistry.register
class IntValueObject(NumericValueObject[int], ABC):
    def __int__(self) -> int:
        return self._validated_value

    def __float__(self) -> float:
        return float(self._validated_value)

    def __round__(self, ndigits: int | None = None) -> Self:
        return self


@VOBaseTypesRegistry.register
class FloatValueObject(NumericValueObject[float], ABC):
    def __int__(self) -> int:
        return int(self._validated_value)

    def __float__(self) -> float:
        return self._validated_value

    def __round__(self, ndigits: int | None = None) -> Self:
        return self.__class__(round(self.value, ndigits))


@VOBaseTypesRegistry.register
class DecimalValueObject(NumericValueObject[Decimal], ABC):
    def __int__(self) -> int:
        return int(self._validated_value)

    def __float__(self) -> float:
        return float(self._validated_value)

    def __round__(self, ndigits: int | None = None) -> Self:
        return self.__class__(self._validated_value.__round__(ndigits or 0))  # python > 3.3


class AnyStrValueObject(ValueObject[typing.AnyStr]):  # type: ignore[misc]
    _validated_value: typing.AnyStr

    @abstractmethod
    def __bytes__(self) -> bytes: ...

    def __reversed__(self) -> Self:
        return self.__class__(typing.cast(typing.AnyStr, reversed(self._validated_value)))

    def __add__(self, other: Self) -> Self:
        self._ensure_same_class(other)
        return self.__class__(self._validated_value + other._validated_value)

    def __len__(self) -> int:
        return len(self._validated_value)

    def __contains__(self, value: typing.AnyStr | Self) -> bool:
        return value in self._validated_value

    def __iter__(self) -> typing.Iterator[typing.AnyStr]:
        return self._validated_value.__iter__()  # type: ignore[return-value]

    def __getitem__(self, item: int) -> typing.AnyStr:
        return self._validated_value[item]  # type: ignore[return-value]

    def startswith(
        self,
        prefix: typing.AnyStr | tuple[typing.AnyStr, ...],
        start: typing.SupportsIndex | None = None,
        end: typing.SupportsIndex | None = None,
    ) -> bool:
        return self._validated_value.startswith(prefix, start, end)


@VOBaseTypesRegistry.register
class StringValueObject(AnyStrValueObject[str], ABC):
    def __bytes__(self) -> bytes:
        return self._validated_value.encode()

    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        return self._validated_value.encode(encoding=encoding, errors=errors)


@VOBaseTypesRegistry.register
class BytesValueObject(AnyStrValueObject[bytes], ABC):
    def __bytes__(self) -> bytes:
        return self._validated_value

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        return self._validated_value.decode(encoding=encoding, errors=errors)


AnyDate = typing.TypeVar("AnyDate", datetime.date, datetime.datetime)


class AnyDateValueObject(ValueObject[AnyDate], ABC):  # type: ignore[misc]
    _validated_value: AnyDate

    def __lt__(self, other: AnyDate | Self) -> bool:
        return self.__compare(other, "__lt__")

    def __le__(self, other: AnyDate | Self) -> bool:
        return self.__compare(other, "__le__")

    def __gt__(self, other: AnyDate | Self) -> bool:
        return self.__compare(other, "__gt__")

    def __ge__(self, other: AnyDate | Self) -> bool:
        return self.__compare(other, "__ge__")

    def __add__(self, other: datetime.timedelta) -> Self:
        self._ensure_timedelta(other)
        return self.__class__(self._validated_value + other)

    @overload
    def __sub__(self, other: "AnyDateValueObject") -> datetime.timedelta: ...

    @overload
    def __sub__(self, other: datetime.timedelta) -> Self: ...

    def __sub__(self, other: "datetime.timedelta | AnyDateValueObject") -> datetime.timedelta | Self:
        match other:
            case datetime.timedelta():
                return self.__class__(self._validated_value - other)
            case AnyDateValueObject():
                return self._validated_value - other._validated_value  # type: ignore[no-any-return]
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

    def replace(self, *args, **kwargs) -> Self:  # type: ignore[no-untyped-def]
        return self.__class__(self._validated_value.replace(*args, **kwargs))

    def _ensure_timedelta(self, other: typing.Any) -> None:
        if not isinstance(other, datetime.timedelta):
            self._raise_unsupported_exc(other)

    def _raise_unsupported_exc(self, other: typing.Any) -> Never:
        raise TypeError(f"unsupported operand type(s) for operation: '{self.__class__}' and '{other.__class__}'")

    def __compare(
        self,
        other: AnyDate | Self,
        method: typing.Literal["__lt__", "__le__", "__gt__", "__ge__"],
    ) -> bool:
        comparison_function: typing.Callable[[Self | datetime.date], bool] = getattr(self._validated_value, method)
        match other:
            case datetime.date():
                return comparison_function(other)
            case AnyDateValueObject():
                return comparison_function(other._validated_value)
            case _:
                self._raise_unsupported_exc(other)


@VOBaseTypesRegistry.register
class DateValueObject(AnyDateValueObject[datetime.date], ABC): ...


@VOBaseTypesRegistry.register
class DatetimeValueObject(AnyDateValueObject[datetime.datetime], ABC):
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


DictKey = typing.TypeVar("DictKey", bound=typing.Hashable)
DictValue = typing.TypeVar("DictValue", covariant=True)
_DefaultValue = typing.TypeVar("_DefaultValue")


@VOBaseTypesRegistry.register
class DictValueObject(ValueObject[dict[DictKey, DictValue]], ABC):  # type: ignore[misc]
    def __iter__(self) -> typing.Iterator[DictKey]:
        return self._validated_value.__iter__()  # type: ignore[no-any-return]

    def __len__(self) -> int:
        return len(self._validated_value)

    def __getitem__(self, __key: DictKey) -> DictValue:
        return self._validated_value[__key]  # type: ignore[no-any-return]

    def get(self, __key: DictKey, default: DictValue | _DefaultValue | None = None) -> DictValue | _DefaultValue | None:
        return self._validated_value.get(__key, default)  # type: ignore[no-any-return]

    def items(self) -> typing.ItemsView[DictKey, DictValue]:
        return self._validated_value.items()  # type: ignore[no-any-return]

    def keys(self) -> typing.KeysView[DictKey]:
        return self._validated_value.keys()  # type: ignore[no-any-return]

    def values(self) -> typing.ValuesView[DictValue]:
        return self._validated_value.values()  # type: ignore[no-any-return]

    def __contains__(self, __o: object) -> typing.TypeGuard[DictKey]:
        return __o in self._validated_value
