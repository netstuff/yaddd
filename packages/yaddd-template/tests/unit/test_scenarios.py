"""Unit tests for declarative order scenarios.

These tests exercise the scenario runner and the place-order workflow in
memory: no database, no broker. They prove that conditional steps, branching
and state mutation behave as declared.
"""

from collections.abc import Mapping
from types import TracebackType
from typing import Any
from uuid import UUID

from yaddd import Mapper, ScenarioRunner, step
from yaddd.application.handlers import Context
from yaddd.domain.entities import AggregateRoot

from app.application.commands import PlaceOrder
from app.application.dto import OrderDTO
from app.application.notifications import NotificationSender
from app.application.scenarios import (
    DISCOUNT_RATE,
    MINIMUM_DISCOUNT_TOTAL,
    AmendOrderScenario,
    OrderScenarioState,
    PlaceOrderScenario,
)
from app.application.uow import OrderRepositories
from app.domain.orders.aggregates.order import Order
from app.domain.orders.value_objects import Money, OrderReference
from tests.shared.constants import TEST_CARD_TOKEN


class FakeNotificationSender(NotificationSender):
    """Records notification calls for assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Mapping[str, Any]]] = []

    async def send(self, *, event_type: str, payload: Mapping[str, Any]) -> None:
        self.calls.append((event_type, payload))


async def test_scenario_applies_discount_for_high_totals() -> None:
    notifier = FakeNotificationSender()
    command = PlaceOrder(reference="ORD-AAAAAAAA", total=MINIMUM_DISCOUNT_TOTAL)
    state = OrderScenarioState(command=command, notifier=notifier)

    class DiscountOnlyScenario(PlaceOrderScenario):
        @step
        async def persist_order(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
            return context.state

    result_state = await ScenarioRunner[OrderScenarioState]().run(
        [DiscountOnlyScenario(uow=_FakeUow(), mapper=_FakeMapper())],
        initial_state=state,
    )

    assert result_state.order is not None
    assert result_state.order.total.value == int(MINIMUM_DISCOUNT_TOTAL * 0.9)


async def test_scenario_skips_payment_step_without_card_token() -> None:
    notifier = FakeNotificationSender()
    command = PlaceOrder(reference="ORD-BBBBBBBB", total=500)
    state = OrderScenarioState(command=command, notifier=notifier)

    class NoPersistScenario(PlaceOrderScenario):
        @step
        async def persist_order(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
            return context.state

    result_state = await ScenarioRunner[OrderScenarioState]().run(
        [NoPersistScenario(uow=_FakeUow(), mapper=_FakeMapper())],
        initial_state=state,
    )

    assert result_state.charged is False


async def test_scenario_records_payment_when_card_token_present() -> None:
    notifier = FakeNotificationSender()
    command = PlaceOrder(reference="ORD-CCCCCCCC", total=500, card_token=TEST_CARD_TOKEN)
    state = OrderScenarioState(command=command, notifier=notifier)

    class NoPersistScenario(PlaceOrderScenario):
        @step
        async def persist_order(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
            return context.state

    result_state = await ScenarioRunner[OrderScenarioState]().run(
        [NoPersistScenario(uow=_FakeUow(), mapper=_FakeMapper())],
        initial_state=state,
    )

    assert result_state.charged is True


async def test_scenario_branches_to_notification() -> None:
    notifier = FakeNotificationSender()
    command = PlaceOrder(reference="ORD-DDDDDDDD", total=500)
    state = OrderScenarioState(command=command, notifier=notifier)

    class BuildAndBranch(PlaceOrderScenario):
        @step
        async def persist_order(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
            return context.state

    result_state = await ScenarioRunner[OrderScenarioState]().run(
        [BuildAndBranch(uow=_FakeUow(), mapper=_FakeMapper())],
        initial_state=state,
    )

    assert result_state.notification_sent is True
    assert len(notifier.calls) == 1
    event_type, payload = notifier.calls[0]
    assert event_type == "OrderPlaced"
    assert isinstance(UUID(str(payload["order_id"])), UUID)


async def test_tiny_order_skips_notification() -> None:
    notifier = FakeNotificationSender()
    command = PlaceOrder(reference="ORD-AAAAAAAA", total=50)
    state = OrderScenarioState(command=command, notifier=notifier)

    class BuildAndBranch(PlaceOrderScenario):
        @step
        async def persist_order(self, context: Context[OrderScenarioState]) -> OrderScenarioState:
            return context.state

    result_state = await ScenarioRunner[OrderScenarioState]().run(
        [BuildAndBranch(uow=_FakeUow(), mapper=_FakeMapper())],
        initial_state=state,
    )

    assert result_state.notification_sent is False
    assert notifier.calls == []


class _FakeUow:
    """Unit of work stand-in that does nothing."""

    @property
    def repos(self) -> OrderRepositories:
        raise NotImplementedError

    def track(self, aggregate: AggregateRoot) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


class _FakeMapper(Mapper[OrderDTO, Order]):
    """Mapper stand-in that returns the aggregate as a DTO-shaped object."""

    def to_dto(self, domain: Order) -> OrderDTO:
        return OrderDTO(
            order_id=domain.id,
            reference=domain.reference.value,
            total=domain.total.value,
            status=domain.status,
        )

    def to_domain(self, dto: OrderDTO) -> Order:
        raise NotImplementedError


async def test_apply_discount_step_is_reusable_across_scenarios() -> None:
    """The same callable step can be arranged in any scenario that shares the
    same context state, not only in the one where it was first declared.
    """
    notifier = FakeNotificationSender()
    command = PlaceOrder(reference="ORD-1234ABCD", total=MINIMUM_DISCOUNT_TOTAL)
    order = Order(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        reference=OrderReference("ORD-1234ABCD"),
        total=Money(MINIMUM_DISCOUNT_TOTAL),
    )
    state = OrderScenarioState(command=command, notifier=notifier, order=order)

    result_state = await ScenarioRunner[OrderScenarioState]().run(
        [AmendOrderScenario()],
        initial_state=state,
    )

    assert result_state.order is not None
    assert result_state.order.total.value == int(MINIMUM_DISCOUNT_TOTAL * DISCOUNT_RATE)
    assert any(s.name == "apply_discount" for s in PlaceOrderScenario(uow=_FakeUow(), mapper=_FakeMapper()).steps)
    assert any(s.name == "apply_discount" for s in AmendOrderScenario().steps)
