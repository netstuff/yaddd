from uuid import UUID, uuid4

import pytest

from yaddd.domain import AggregateRoot, CrudRepository
from yaddd.exceptions import EntityNotFoundError
from yaddd.infrastructure import InMemoryCrudRepository


class Order(AggregateRoot):
    id: UUID
    status: str
    total: int


@pytest.fixture
def repo() -> InMemoryCrudRepository[Order]:
    return InMemoryCrudRepository()


async def test_create_and_get(repo: InMemoryCrudRepository[Order]):
    order = Order(id=uuid4(), status="new", total=10)
    await repo.create(order)

    assert await repo.get(order.pk) == order


async def test_get_missing_returns_none(repo: InMemoryCrudRepository[Order]):
    assert await repo.get(uuid4()) is None


async def test_update_existing(repo: InMemoryCrudRepository[Order]):
    order = Order(id=uuid4(), status="new", total=10)
    await repo.create(order)

    updated = Order(id=order.pk, status="paid", total=10)
    await repo.update(updated)

    stored = await repo.get(order.pk)
    assert stored is not None
    assert stored.status == "paid"


async def test_update_missing_raises(repo: InMemoryCrudRepository[Order]):
    with pytest.raises(EntityNotFoundError, match="Order"):
        await repo.update(Order(id=uuid4(), status="new", total=10))


async def test_delete(repo: InMemoryCrudRepository[Order]):
    order = Order(id=uuid4(), status="new", total=10)
    await repo.create(order)

    await repo.delete(order.pk)

    assert await repo.get(order.pk) is None


async def test_delete_missing_is_idempotent(repo: InMemoryCrudRepository[Order]):
    await repo.delete(uuid4())


async def test_read_with_filter(repo: InMemoryCrudRepository[Order]):
    await repo.create(Order(id=uuid4(), status="new", total=10))
    await repo.create(Order(id=uuid4(), status="paid", total=20))
    await repo.create(Order(id=uuid4(), status="paid", total=30))

    paid = await repo.read({"status": "paid"})

    assert len(paid) == 2
    assert all(order.status == "paid" for order in paid)


async def test_read_with_slice(repo: InMemoryCrudRepository[Order]):
    for total in (10, 20, 30):
        await repo.create(Order(id=uuid4(), status="new", total=total))

    assert len(await repo.read()) == 3
    assert len(await repo.read(slice=(1, 1))) == 1
    assert len(await repo.read(slice=(2, 0))) == 1


async def test_structural_conformance_to_port(repo: InMemoryCrudRepository[Order]):
    port: CrudRepository[Order] = repo
    order = Order(id=uuid4(), status="new", total=10)
    await port.create(order)
    assert await port.get(order.pk) == order
