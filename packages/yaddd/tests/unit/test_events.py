from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from yaddd.domain import DomainEvent


class OrderPlaced(DomainEvent):
    order_id: object


def test_event_occurred_at_defaults_to_utc_now():
    before = datetime.now(UTC)
    event = OrderPlaced(order_id=uuid4())
    after = datetime.now(UTC)

    assert before <= event.occurred_at <= after


def test_event_is_frozen():
    event = OrderPlaced(order_id=uuid4())
    with pytest.raises(FrozenInstanceError):
        event.order_id = uuid4()  # type: ignore[misc]


def test_event_fields_are_kw_only():
    with pytest.raises(TypeError):
        OrderPlaced(uuid4())  # type: ignore[misc]


def test_event_name_is_class_name():
    assert type(OrderPlaced(order_id=uuid4())).__name__ == "OrderPlaced"
