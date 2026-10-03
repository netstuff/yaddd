from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from yaddd.application import Command, Query


class PlaceOrder(Command):
    order_id: UUID
    total: int


class GetOrder(Query):
    order_id: UUID


def test_command_is_frozen_and_kw_only():
    command = PlaceOrder(order_id=uuid4(), total=10)
    with pytest.raises(FrozenInstanceError):
        command.total = 20  # type: ignore[misc]
    with pytest.raises(TypeError):
        PlaceOrder(uuid4(), 10)  # type: ignore[misc]


def test_query_is_frozen_and_kw_only():
    query = GetOrder(order_id=uuid4())
    with pytest.raises(FrozenInstanceError):
        query.order_id = uuid4()  # type: ignore[misc]
    with pytest.raises(TypeError):
        GetOrder(uuid4())  # type: ignore[misc]


def test_command_holds_payload():
    order_id = uuid4()
    command = PlaceOrder(order_id=order_id, total=10)
    assert command.order_id == order_id
    assert command.total == 10
