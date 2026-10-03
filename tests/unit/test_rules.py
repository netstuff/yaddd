import pytest

from yaddd.domain import BusinessRule
from yaddd.exceptions import BusinessRuleViolationError


class IsAdult(BusinessRule[int]):
    message = "must be adult"

    def is_satisfied_by(self, candidate: int) -> bool:
        return candidate >= 18


class IsPositive(BusinessRule[int]):
    def is_satisfied_by(self, candidate: int) -> bool:
        return candidate > 0


def test_check_passes_when_satisfied():
    IsAdult().check(18)


def test_check_raises_with_message():
    with pytest.raises(BusinessRuleViolationError, match="must be adult"):
        IsAdult().check(17)


def test_check_falls_back_to_class_name_without_message():
    with pytest.raises(BusinessRuleViolationError, match="IsPositive is not satisfied"):
        IsPositive().check(0)


def test_rules_compose_like_specifications():
    rule = IsAdult() & IsPositive()
    assert rule.is_satisfied_by(20)
    assert not rule.is_satisfied_by(10)


def test_repr_is_class_name():
    assert repr(IsAdult()) == str(IsAdult()) == "IsAdult"
