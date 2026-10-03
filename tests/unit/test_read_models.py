from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from yaddd.domain.entities import PrimaryKey
from yaddd.infrastructure import ReadModel, ReadModelRepository


class OrderSummary(ReadModel):
    order_id: str
    total: int


class InMemoryOrderSummaries:
    def __init__(self, rows: list[OrderSummary]) -> None:
        self._rows = rows

    async def find(self, filter: dict | None = None, *, slice: tuple[int, int] = (0, 0)) -> list[OrderSummary]:
        rows = self._rows
        if filter:
            rows = [row for row in rows if all(getattr(row, key, None) == value for key, value in filter.items())]
        offset, limit = slice
        return rows[offset:] if limit == 0 else rows[offset : offset + limit]

    async def find_one(self, pk: PrimaryKey) -> OrderSummary | None:
        return next((row for row in self._rows if row.order_id == str(pk)), None)


def test_read_model_is_frozen_and_kw_only():
    row = OrderSummary(order_id="x", total=10)
    with pytest.raises(FrozenInstanceError):
        row.total = 20  # type: ignore[misc]
    with pytest.raises(TypeError):
        OrderSummary("x", 10)  # type: ignore[misc]


async def test_read_model_repository_find():
    order_id = uuid4()
    rows = [OrderSummary(order_id=str(order_id), total=10), OrderSummary(order_id=str(uuid4()), total=20)]
    repo: ReadModelRepository[OrderSummary] = InMemoryOrderSummaries(rows)

    assert await repo.find({"total": 10}) == [rows[0]]
    assert await repo.find(slice=(1, 0)) == rows[1:]
    assert await repo.find_one(order_id) == rows[0]
    assert await repo.find_one(uuid4()) is None


def test_read_model_carries_no_invariants():
    row = OrderSummary(order_id="x", total=-999)
    assert row.total == -999
