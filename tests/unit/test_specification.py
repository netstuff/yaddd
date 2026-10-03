from dataclasses import dataclass

from yaddd.shared.specification import Specification


class IsEven(Specification[int]):
    def is_satisfied_by(self, candidate: int) -> bool:
        return candidate % 2 == 0


class IsOdd(Specification[int]):
    def is_satisfied_by(self, candidate: int) -> bool:
        return candidate % 2 == 1


@dataclass(frozen=True)
class MoreThan(Specification[int]):
    limit: int

    def is_satisfied_by(self, candidate: int) -> bool:
        return candidate > self.limit


def test_spec_is_satisfied():
    spec = IsEven()
    assert spec.is_satisfied_by(2)
    assert not spec.is_satisfied_by(3)


def test_invert_base():
    base_spec = IsEven()
    spec = ~base_spec
    assert spec.is_satisfied_by(1)
    assert not spec.is_satisfied_by(2)


def test_and_spec():
    is_even = IsEven()
    is_odd = IsOdd()
    spec = is_even & is_odd
    assert not spec.is_satisfied_by(2)
    assert not spec.is_satisfied_by(1)

    more_than_one = MoreThan(1)
    assert (more_than_one & is_even).is_satisfied_by(2)


def test_or_spec():
    is_even = IsEven()
    is_odd = IsOdd()
    spec = is_even | is_odd

    assert spec.is_satisfied_by(1)
    assert spec.is_satisfied_by(2)
    assert not spec.is_satisfied_by(3.5)


def test_not_spec():
    is_even = IsEven()
    is_odd = IsOdd()
    assert ~is_odd.is_satisfied_by(2)
    assert ~is_even.is_satisfied_by(1)

    assert ((~is_even) | (~is_odd)).is_satisfied_by(3)
    assert not ((~is_even) & (~is_odd)).is_satisfied_by(2)


def test_xor_spec():
    more_than_five = MoreThan(5)
    is_even = IsEven()
    xor_spec = is_even ^ more_than_five

    assert xor_spec.is_satisfied_by(4)
    assert xor_spec.is_satisfied_by(7)
    assert not xor_spec.is_satisfied_by(8)
