"""Unit tests: the domain, value objects and the rules that guard them."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from yaddd import BusinessRuleViolationError, InvariantViolationError, SensitiveValueAccessError

from app.domain.orders.aggregates.order import Order
from app.domain.orders.constants import OrderErrorMessage, OrderStatus
from app.domain.orders.events import OrderPaid, OrderPlaced
from app.domain.orders.rules import OrderMustBePlaced, TotalMustBePositive
from app.domain.orders.value_objects import CardToken, Money, OrderReference
from tests.shared.constants import TEST_CARD_TOKEN, TEST_REFERENCE, TEST_TOTAL


def new_order(
    reference: str | None = None,
    total: int = TEST_TOTAL,
    card_token: str | None = None,
) -> Order:
    """Build an order with a unique reference unless one is given."""
    return Order(
        id=uuid4(),
        reference=OrderReference(reference or f"ORD-{uuid4().hex[:8].upper()}"),
        total=Money(total),
        card_token=CardToken(card_token) if card_token is not None else None,
    )


def test_place_marks_placed_and_emits_event() -> None:
    order = new_order()

    order.place()

    assert order.status == OrderStatus.PLACED
    events = order.pull_events()
    assert [type(event) for event in events] == [OrderPlaced]
    placed = events[0]
    assert isinstance(placed, OrderPlaced)
    assert placed.order_id == order.id
    assert placed.total == order.total.value
    assert placed.reference == order.reference.value


def test_pull_events_empties_the_stream() -> None:
    order = new_order()
    order.place()

    assert len(order.pull_events()) == 1
    assert order.pull_events() == []


def test_mark_paid_requires_placed_order() -> None:
    order = new_order()

    with pytest.raises(BusinessRuleViolationError, match=OrderErrorMessage.ORDER_MUST_BE_PLACED):
        order.mark_paid()


def test_mark_paid_emits_order_paid() -> None:
    order = new_order()
    order.place()
    order.pull_events()

    order.mark_paid()

    assert order.status == OrderStatus.PAID
    events = order.pull_events()
    assert [type(event) for event in events] == [OrderPaid]


def test_zero_total_violates_the_invariant() -> None:
    with pytest.raises(InvariantViolationError, match=TotalMustBePositive.__name__):
        new_order(total=0)


def test_invariants_are_rechecked_on_construction() -> None:
    stored = Order(
        id=uuid4(),
        reference=OrderReference(TEST_REFERENCE),
        total=Money(1),
        status=OrderStatus.PAID,
    )

    with pytest.raises(InvariantViolationError):
        Order(id=stored.id, reference=stored.reference, total=Money(0), status=stored.status)


def test_rules_compose_with_boolean_operators() -> None:
    order = new_order()
    placed = Order(
        id=order.id,
        reference=order.reference,
        total=order.total,
        status=OrderStatus.PLACED,
    )

    both = TotalMustBePositive() & OrderMustBePlaced()

    assert both.is_satisfied_by(placed)
    assert not OrderMustBePlaced().is_satisfied_by(order)


@pytest.mark.parametrize("raw", ["ORD-1234", "ord-1A2B3C4D", "1A2B3C4D", "ORD-1A2B3C4"])
def test_order_reference_rejects_malformed_values(raw: str) -> None:
    with pytest.raises(ValidationError):
        OrderReference(raw)


def test_rule_message_is_readable() -> None:
    assert TotalMustBePositive.message == OrderErrorMessage.TOTAL_MUST_BE_POSITIVE


def test_money_rejects_out_of_range_totals() -> None:
    with pytest.raises(ValidationError):
        Money(-1)
    with pytest.raises(ValidationError):
        Money(1_000_000_000)


def test_card_token_is_masked_in_repr_and_raises_on_str() -> None:
    token = CardToken(TEST_CARD_TOKEN)

    assert TEST_CARD_TOKEN not in repr(token)
    assert repr(token) == "CardToken([MASKED])"
    with pytest.raises(SensitiveValueAccessError):
        str(token)


def test_value_objects_compare_by_value_and_type() -> None:
    assert Money(500) == Money(500)
    assert Money(500) != Money(501)
    assert OrderReference(TEST_REFERENCE) == OrderReference(TEST_REFERENCE)
