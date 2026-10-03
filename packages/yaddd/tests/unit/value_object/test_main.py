import datetime
from decimal import Decimal
from typing import Any

import pytest

from yaddd.domain.value_object import (
    AnyStrValueObject,
    BytesValueObject,
    DateValueObject,
    DecimalValueObject,
    FloatValueObject,
    IntValueObject,
    NumericValueObject,
    StringValueObject,
    ValueObject,
)
from yaddd.domain.value_object.base_types import AnyDateValueObject, DatetimeValueObject, DictValueObject


class _TestTypeMixin:
    @classmethod
    def validate(cls, value):
        return value


def test_base_vo():
    class OptimistObject:
        """Has more value, than anybody."""

        def __eq__(self, other):
            return isinstance(other, self.__class__)

        def __lt__(self, other: Any) -> bool:
            return False

        def __le__(self, other: Any) -> bool:
            return False

        def __gt__(self, other: Any) -> bool:
            return True

        def __ge__(self, other: Any) -> bool:
            return True

    class TestType(_TestTypeMixin, ValueObject[OptimistObject]): ...

    test_value = TestType(OptimistObject())

    assert test_value > test_value
    assert test_value >= test_value
    assert not test_value < test_value
    assert not test_value <= test_value
    assert test_value == TestType(OptimistObject())
    assert test_value is not None
    assert test_value != 1


def test_numeric_vo():
    class PositiveInt(int):
        def __new__(cls, value: int):
            if value <= 0:
                raise ValueError(f"Not positive: {value}")
            return super().__new__(cls, value)

        def __sub__(self, other):
            return self.__class__(super().__sub__(other))

        def __add__(self, other):
            return self.__class__(super().__add__(other))

        def __neg__(self):
            raise ValueError(f"Stay positive!")

        def __str__(self):
            return f"PositiveInt({super().__str__()})"

    class TestType(_TestTypeMixin, NumericValueObject[PositiveInt]):
        def __int__(self) -> int:
            return self._validated_value

        def __float__(self) -> float:
            return float(self._validated_value)

        def __round__(self, n=None):
            return self._validated_value

    test_value1 = TestType(PositiveInt(1))
    test_value2 = TestType(PositiveInt(2))

    assert test_value1 + test_value2 == TestType(PositiveInt(3))

    with pytest.raises(TypeError, match="unsupported operand"):
        assert test_value1 + 3  # PyCharm highlights other value
    with pytest.raises(TypeError, match="unsupported operand"):
        assert 3 + test_value1  # PyCharm highlights other value

    assert test_value2 - test_value1 == TestType(PositiveInt(1))

    with pytest.raises(ValueError, match="Not positive"):
        assert test_value1 - test_value2

    with pytest.raises(TypeError, match="unsupported operand"):
        assert test_value1 - 3  # PyCharm highlights other value
    with pytest.raises(TypeError, match="unsupported operand"):
        assert 3 - test_value1  # PyCharm highlights other value

    test_value1 += test_value2
    assert test_value1 == TestType(PositiveInt(3))
    test_value1 -= test_value2
    assert test_value1 == TestType(PositiveInt(1))

    with pytest.raises(ValueError, match="Stay positive!"):
        assert -test_value1

    assert +test_value1 == test_value1
    assert abs(test_value1) == test_value1


def test_int_vo():
    class TestType(_TestTypeMixin, IntValueObject): ...

    test_value = TestType(1)
    assert int(test_value) == 1
    assert float(test_value) == 1.0
    assert round(test_value) == test_value


def test_float_vo():
    class TestType(_TestTypeMixin, FloatValueObject): ...

    test_value = TestType(1.25)
    assert int(test_value) == 1
    assert float(test_value) == 1.25
    assert round(test_value) == TestType(1.0)


def test_decimal_vo():
    class TestType(_TestTypeMixin, DecimalValueObject): ...

    test_value = TestType(Decimal(100.0001))
    assert int(test_value) == 100
    assert float(test_value) == 100.0001
    assert round(test_value) == TestType(Decimal(100))


def test_anystr_vo():
    class UpperStr(str):
        def __new__(cls, value: str):
            return super().__new__(cls, value.upper())

        def __add__(self, other):
            return self.__class__(super().__add__(other))

        def __str__(self):
            return f"UpperStr({super().__str__()})"

    class TestType(_TestTypeMixin, AnyStrValueObject[UpperStr]):
        def __bytes__(self) -> bytes:
            return bytes(self)

    test_value1 = TestType(UpperStr("qwe"))
    test_value2 = TestType(UpperStr("rty"))

    assert test_value1 + test_value2 == TestType(UpperStr("QWERTY"))

    with pytest.raises(TypeError, match="unsupported operand"):
        assert test_value1 + "3"  # PyCharm highlights other value
    with pytest.raises(TypeError, match="unsupported operand"):
        assert 3 + test_value1  # PyCharm highlights other value

    test_value1 += test_value2
    assert test_value1 == TestType(UpperStr("qwerty"))
    assert len(test_value1) == len("QWERTY")
    assert UpperStr("q") in test_value1
    assert "".join(_ for _ in test_value1) == "QWERTY"
    assert test_value1[0] == UpperStr("q")
    assert test_value1.startswith(UpperStr("q"))


def test_string_vo():
    class TestType(_TestTypeMixin, StringValueObject): ...

    test_value = TestType("test string")
    assert bytes(test_value) == b"test string"
    assert test_value.encode() == b"test string"


def test_bytes_vo():
    class TestType(_TestTypeMixin, BytesValueObject): ...

    test_value = TestType(b"test string")
    assert bytes(test_value) == b"test string"
    assert test_value.decode() == "test string"


def _test_date_vo(earlier, later, latest, cls: type[AnyDateValueObject]):
    assert earlier < later < latest, "args incompatibility"
    earlier_test_value, later_test_value = cls(earlier), cls(later)

    assert earlier_test_value < later_test_value < latest
    assert earlier_test_value <= later_test_value <= latest
    assert latest > later_test_value > earlier_test_value
    assert latest >= later_test_value >= earlier_test_value

    assert (arg_timedelta := later_test_value - earlier_test_value)
    assert later_test_value - earlier_test_value == arg_timedelta

    with pytest.raises(TypeError, match="unsupported operand type"):
        assert earlier_test_value + later_test_value  # PyCharm highlights other value

    assert earlier_test_value + arg_timedelta == later_test_value

    earlier_test_value += arg_timedelta
    assert earlier_test_value == later_test_value
    earlier_test_value -= arg_timedelta
    assert earlier_test_value.value == earlier

    assert earlier_test_value.year == earlier.year
    assert earlier_test_value.month == earlier.month
    assert earlier_test_value.day == earlier.day
    assert earlier_test_value.timetuple() == earlier.timetuple()
    assert earlier_test_value.toordinal() == earlier.toordinal()
    assert earlier_test_value.weekday() == earlier.weekday()
    assert earlier_test_value.isoweekday() == earlier.isoweekday()
    assert earlier_test_value.isocalendar() == earlier.isocalendar()
    assert earlier_test_value.isoformat() == earlier.isoformat()
    assert earlier_test_value.ctime() == earlier.ctime()
    assert earlier_test_value.strftime("Y") == earlier.strftime("Y")
    replaced_test_value = earlier_test_value.replace(year=latest.year)
    assert replaced_test_value.year == latest.year


def test_date_vo():
    class TestType(_TestTypeMixin, DateValueObject): ...

    earlier_date = datetime.date(1970, 1, 1)
    later_date = datetime.date(2000, 1, 1)
    latest_date = datetime.date(3535, 1, 1)

    _test_date_vo(earlier_date, later_date, latest_date, cls=TestType)


def test_datetime_vo():
    class TestType(_TestTypeMixin, DatetimeValueObject): ...

    earlier_datetime = datetime.datetime(1970, 1, 1, 0, 0, 0)
    later_datetime = datetime.datetime(2000, 1, 1, 0, 0, 0)
    latest = datetime.datetime(3535, 1, 1, 0, 0, 0)

    _test_date_vo(earlier_datetime, later_datetime, latest, cls=TestType)

    earlier_test_value = TestType(earlier_datetime)

    assert earlier_test_value.hour == earlier_datetime.hour
    assert earlier_test_value.minute == earlier_datetime.minute
    assert earlier_test_value.second == earlier_datetime.second
    assert earlier_test_value.microsecond == earlier_datetime.microsecond
    assert earlier_test_value.tzinfo == earlier_datetime.tzinfo
    assert earlier_test_value.fold == earlier_datetime.fold
    assert earlier_test_value.date() == earlier_datetime.date()
    assert earlier_test_value.timestamp() == earlier_datetime.timestamp()
    assert earlier_test_value.utcoffset() == earlier_datetime.utcoffset()
    assert earlier_test_value.tzname() == earlier_datetime.tzname()
    assert earlier_test_value.dst() == earlier_datetime.dst()
    assert earlier_test_value.astimezone() == earlier_datetime.astimezone()


def test_dict_vo():
    class TestType(_TestTypeMixin, DictValueObject[str, int]): ...

    assert TestType({"a": "1", "b": "2"})  # PyCharm highlights
    assert TestType({"a": 1, "b": "2"})  # PyCharm permits

    test_value = TestType({"a": 1, "b": 2})

    with pytest.raises(TypeError, match="'>' not supported between instances of 'dict' and 'dict'"):
        assert test_value > test_value

    assert len(test_value) == 2
    assert test_value["a"] == 1 == test_value.get("a")
    assert test_value["b"] == 2 == test_value.get("b")
    assert test_value.get("c") is None
    assert test_value.get("c", 3) == 3
    assert test_value.get("c", 0) == 0

    assert "a" in test_value
    assert "b" in test_value
    assert 1 not in test_value  # IDE permits

    for iter_k, keys_k in zip(test_value, test_value.keys()):
        assert iter_k == keys_k

    for (items_k, items_v), values_v in zip(test_value.items(), test_value.values()):
        assert items_v == values_v == test_value.value.get(items_k)
