from typing import Any
from uuid import UUID, uuid4

import pytest

from yaddd.domain import AggregateRoot, BusinessRule, DomainEvent, Entity
from yaddd.exceptions import InvariantViolationError


class User(Entity):
    id: UUID
    name: str


class Order(Entity):
    id: UUID
    total: int


class _PositiveTotal(BusinessRule[Any]):
    message = "total must be positive"

    def is_satisfied_by(self, candidate: Any) -> bool:
        return candidate.total > 0


class _PositiveQuantity(BusinessRule[Any]):
    message = "quantity must be positive"

    def is_satisfied_by(self, candidate: Any) -> bool:
        return candidate.quantity > 0


class OrderLine(Entity):
    id: UUID
    quantity: int

    INVARIANTS = (_PositiveQuantity(),)


class OrderPlaced(DomainEvent):
    order_id: UUID


class PlacedOrder(AggregateRoot):
    id: UUID
    total: int

    INVARIANTS = (_PositiveTotal(),)


def test_entity_equality_by_identity():
    uid = uuid4()
    assert User(id=uid, name="alice") == User(id=uid, name="bob")


def test_entity_not_equal_on_different_pk():
    assert User(id=uuid4(), name="alice") != User(id=uuid4(), name="alice")


def test_entity_not_equal_across_classes():
    uid = uuid4()
    assert User(id=uid, name="alice") != Order(id=uid, total=1)


def test_entity_hash_by_pk():
    uid = uuid4()
    assert hash(User(id=uid, name="alice")) == hash(User(id=uid, name="bob"))


def test_entity_fields_are_kw_only():
    with pytest.raises(TypeError):
        User(uuid4(), "alice")  # type: ignore[misc]


def test_entity_to_dict():
    uid = uuid4()
    assert User(id=uid, name="alice").to_dict() == {"id": uid, "name": "alice"}


def test_entity_invariants_checked_on_construction():
    OrderLine(id=uuid4(), quantity=1)
    with pytest.raises(InvariantViolationError, match="Invariant violated: _PositiveQuantity"):
        OrderLine(id=uuid4(), quantity=0)


def test_aggregate_invariants_pass():
    PlacedOrder(id=uuid4(), total=10)


def test_aggregate_invariant_violation():
    with pytest.raises(InvariantViolationError, match="Invariant violated: _PositiveTotal"):
        PlacedOrder(id=uuid4(), total=-1)


def test_aggregate_events_collected_and_pulled():
    order = PlacedOrder(id=uuid4(), total=10)
    event = OrderPlaced(order_id=order.pk)

    order.add_event(event)
    assert order.pull_events() == [event]
    assert order.pull_events() == []
