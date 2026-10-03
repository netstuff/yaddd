import pytest

from yaddd.domain.value_object import SensitiveValueObject, ValueObject
from yaddd.exceptions import SensitiveValueAccessError


class _Secret(SensitiveValueObject[str]):
    @classmethod
    def validate(cls, value: str) -> str:
        return value


class _SecretChild(_Secret):
    pass


class _Public(ValueObject[str]):
    @classmethod
    def validate(cls, value: str) -> str:
        return value


def test_sensitive_repr_is_masked():
    assert repr(_Secret("hidden")) == "_Secret([MASKED])"


def test_sensitive_str_raises():
    with pytest.raises(SensitiveValueAccessError, match="Access to _Secret is not allowed"):
        str(_Secret("hidden"))


def test_sensitive_masking_is_inherited():
    assert repr(_SecretChild("hidden")) == "_SecretChild([MASKED])"
    with pytest.raises(SensitiveValueAccessError, match="Access to _SecretChild is not allowed"):
        str(_SecretChild("hidden"))


def test_non_sensitive_vo_is_not_masked():
    vo = _Public("visible")
    assert repr(vo) == "_Public('visible')"
    assert str(vo) == "visible"
