from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from yaddd.domain import AggregateRoot, BusinessRule, DomainEvent, Factory
from yaddd.exceptions import InvariantViolationError


class _PositiveTotal(BusinessRule):
    message = "total must be positive"

    def is_satisfied_by(self, candidate) -> bool:
        return candidate.total > 0


class OrderCreated(DomainEvent):
    order_id: UUID


class Order(AggregateRoot):
    id: UUID
    total: int

    INVARIANTS = (_PositiveTotal(),)


@dataclass(frozen=True)
class NewOrder:
    total: int


class OrderFactory:
    """Creates new orders: allocates identity and records the created event."""

    def __init__(self, id_generator) -> None:
        self._id_generator = id_generator

    def create(self, data: NewOrder) -> Order:
        order = Order(id=self._id_generator(), total=data.total)
        order.add_event(OrderCreated(order_id=order.pk))
        return order


def test_factory_creates_aggregate_with_generated_identity():
    factory: Factory[NewOrder, Order] = OrderFactory(uuid4)

    order = factory.create(NewOrder(total=100))

    assert isinstance(order.pk, UUID)
    assert order.total == 100


def test_factory_records_created_event():
    factory = OrderFactory(uuid4)

    order = factory.create(NewOrder(total=100))

    events = order.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], OrderCreated)
    assert events[0].order_id == order.pk


def test_factory_cannot_create_invalid_aggregate():
    factory = OrderFactory(uuid4)

    with pytest.raises(InvariantViolationError, match="Invariant violated"):
        factory.create(NewOrder(total=-5))
