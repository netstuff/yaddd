"""Integration tests: handlers, unit of work and SQLAlchemy repositories.

Everything runs against a real (file-backed SQLite) database through the same
adapters production uses, so constraints and transaction ownership are
exercised for real. SQLite cannot do concurrent writers, so rollback is proven
by observing that nothing was published and nothing was stored after a failure.
"""

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from yaddd import BusinessRuleViolationError, DomainEvent, EntityNotFoundError

from app.application.commands import MarkOrderPaid, PlaceOrder
from app.application.dto import OrderDTO
from app.application.handlers import MarkOrderPaidHandler, PlaceOrderHandler
from app.application.mappers import OrderMapper
from app.application.messaging import EventEnvelope
from app.application.projections import OrderPlacedProjector
from app.application.read_models import OrderPlacementRepository
from app.application.uow import OrderUnitOfWork
from app.domain.orders.aggregates.order import Order
from app.domain.orders.constants import OrderStatus
from app.domain.orders.events import OrderPaid, OrderPlaced
from app.domain.orders.value_objects import CardToken, Money, OrderReference
from app.infrastructure.database.constants import OrderPlacementColumn
from app.infrastructure.database.models import order_placements_table, orders_table
from app.infrastructure.database.read_models import SqlOrderPlacementRepository
from tests.shared.constants import TEST_TOTAL


def new_reference() -> str:
    """A unique, well-formed order reference."""
    return f"ORD-{uuid4().hex[:8].upper()}"


async def place_order(
    make_uow: Callable[[], OrderUnitOfWork],
    reference: str | None = None,
    total: int = TEST_TOTAL,
    card_token: str | None = None,
) -> OrderDTO:
    """Run the place-order use case and return what it reported."""
    command = PlaceOrder(
        reference=reference or new_reference(),
        total=total,
        card_token=card_token,
    )
    async with make_uow() as uow:
        return await PlaceOrderHandler(uow, OrderMapper())(command)


async def get_order(make_uow: Callable[[], OrderUnitOfWork], order_id: UUID) -> Order | None:
    """Read one aggregate back through the repository port."""
    async with make_uow() as uow:
        return await uow.repos.orders.get(order_id)


async def count_orders(session_maker: async_sessionmaker[AsyncSession]) -> int:
    """How many order rows the database currently holds."""
    async with session_maker() as session:
        result = await session.execute(select(func.count()).select_from(orders_table))
        return int(result.scalar_one())


async def test_place_order_persists_and_publishes(
    make_uow: Callable[[], OrderUnitOfWork],
    published: list[DomainEvent],
) -> None:
    dto = await place_order(make_uow, total=TEST_TOTAL)

    assert dto.status == OrderStatus.PLACED
    assert dto.total == 1999
    assert [type(event) for event in published] == [OrderPlaced]

    stored = await get_order(make_uow, dto.order_id)
    assert stored is not None
    assert stored.total == Money(1999)


async def test_placed_event_matches_the_persisted_order(
    make_uow: Callable[[], OrderUnitOfWork],
    published: list[DomainEvent],
) -> None:
    reference = new_reference()
    dto = await place_order(make_uow, reference, 2500)
    placed = next(event for event in published if isinstance(event, OrderPlaced))

    assert placed.order_id == dto.order_id
    assert placed.reference == reference
    assert placed.total == 2500


async def test_duplicate_reference_is_rejected_by_the_database(
    make_uow: Callable[[], OrderUnitOfWork],
) -> None:
    reference = new_reference()
    await place_order(make_uow, reference, 1000)

    with pytest.raises(IntegrityError):
        await place_order(make_uow, reference, 9999)


async def test_failed_transaction_leaves_no_trace(
    make_uow: Callable[[], OrderUnitOfWork],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    reference = new_reference()
    await place_order(make_uow, reference, 1000)

    with pytest.raises(IntegrityError):
        await place_order(make_uow, reference, 2000)

    assert await count_orders(session_maker) == 1


async def test_paying_a_placed_order_publishes_order_paid(
    make_uow: Callable[[], OrderUnitOfWork],
    published: list[DomainEvent],
) -> None:
    dto = await place_order(make_uow, total=3000)
    published.clear()

    async with make_uow() as uow:
        await MarkOrderPaidHandler(uow, OrderMapper())(MarkOrderPaid(order_id=dto.order_id))

    paid = await get_order(make_uow, dto.order_id)
    assert paid is not None
    assert paid.status == OrderStatus.PAID
    assert [type(event) for event in published] == [OrderPaid]


async def test_paying_an_unknown_order_raises_not_found(
    make_uow: Callable[[], OrderUnitOfWork],
) -> None:
    async with make_uow() as uow:
        with pytest.raises(EntityNotFoundError):
            await MarkOrderPaidHandler(uow, OrderMapper())(MarkOrderPaid(order_id=uuid4()))


async def test_paying_an_unplaced_order_changes_nothing(
    make_uow: Callable[[], OrderUnitOfWork],
    published: list[DomainEvent],
) -> None:
    order = Order(id=uuid4(), reference=OrderReference(new_reference()), total=Money(1500))
    async with make_uow() as uow:
        await uow.repos.orders.create(order)
        await uow.commit()
    published.clear()

    async with make_uow() as uow:
        with pytest.raises(BusinessRuleViolationError):
            await MarkOrderPaidHandler(uow, OrderMapper())(MarkOrderPaid(order_id=order.id))

    unchanged = await get_order(make_uow, order.id)
    assert unchanged is not None
    assert unchanged.status == OrderStatus.NEW
    assert published == []


async def test_card_token_is_persisted_and_masked(
    make_uow: Callable[[], OrderUnitOfWork],
) -> None:
    secret = "tok_" + "live_4242"
    dto = await place_order(make_uow, card_token=secret)

    stored = await get_order(make_uow, dto.order_id)

    assert stored is not None
    assert stored.card_token == CardToken(secret)
    assert secret not in repr(stored)


async def test_projection_stores_placed_orders(
    make_uow: Callable[[], OrderUnitOfWork],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    dto = await place_order(make_uow, total=4000)
    repository: OrderPlacementRepository = SqlOrderPlacementRepository(session_maker)

    await OrderPlacedProjector(repository)(
        EventEnvelope.from_event(OrderPlaced(order_id=dto.order_id, reference=dto.reference, total=dto.total))
    )

    stored = await repository.find_one(dto.order_id)
    assert stored is not None
    assert stored.reference == dto.reference
    assert stored.total == dto.total
    assert stored.placed_at.tzinfo is not None


async def test_projection_is_idempotent(
    make_uow: Callable[[], OrderUnitOfWork],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    dto = await place_order(make_uow, total=4100)
    repository: OrderPlacementRepository = SqlOrderPlacementRepository(session_maker)
    projector = OrderPlacedProjector(repository)
    event = EventEnvelope.from_event(OrderPlaced(order_id=dto.order_id, reference=dto.reference, total=dto.total))

    await projector(event)
    await projector(event)

    assert await repository.find_one(dto.order_id) is not None
    async with session_maker() as session:
        result = await session.execute(
            select(func.count())
            .select_from(order_placements_table)
            .where(order_placements_table.c[OrderPlacementColumn.ORDER_ID] == dto.order_id)
        )
        assert int(result.scalar_one()) == 1


async def test_repositories_return_entities_not_rows(
    make_uow: Callable[[], OrderUnitOfWork],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    dto = await place_order(make_uow, total=5000)

    async with make_uow() as uow:
        found = await uow.repos.orders.get(dto.order_id)

    assert isinstance(found, Order)
    assert found.reference == OrderReference(dto.reference)
    assert isinstance(found.id, UUID)
    assert session_maker is not None


async def test_get_returns_none_for_an_unknown_order(
    make_uow: Callable[[], OrderUnitOfWork],
) -> None:
    async with make_uow() as uow:
        assert await uow.repos.orders.get(uuid4()) is None


async def test_read_filters_by_column(
    make_uow: Callable[[], OrderUnitOfWork],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    reference = new_reference()
    dto = await place_order(make_uow, reference, 1234)

    async with make_uow() as uow:
        found = await uow.repos.orders.read({"reference": OrderReference(reference)})

    assert [order.id for order in found] == [dto.order_id]


async def test_events_are_published_only_after_commit(
    make_uow: Callable[[], OrderUnitOfWork],
    published: list[DomainEvent],
) -> None:
    order = Order(id=uuid4(), reference=OrderReference(new_reference()), total=Money(700))
    order.place()

    async with make_uow() as uow:
        await uow.repos.orders.create(order)
        assert published == [], "events must not escape before the transaction commits"

    assert published == [], "an uncommitted unit of work publishes nothing"


async def test_committing_publishes_tracked_events(
    make_uow: Callable[[], OrderUnitOfWork],
    published: list[DomainEvent],
) -> None:
    order = Order(id=uuid4(), reference=OrderReference(new_reference()), total=Money(800))
    order.place()

    async with make_uow() as uow:
        await uow.repos.orders.create(order)
        await uow.commit()

    assert [type(event) for event in published] == [OrderPlaced]
