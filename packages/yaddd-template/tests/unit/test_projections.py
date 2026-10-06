"""Unit tests: event envelopes and the projection they feed."""

from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter

from app.application.dto import OrderPayloadKey, OrderPlacement
from app.application.messaging import EnvelopeKey, EventEnvelope, jsonify
from app.application.projections import OrderPlacedProjector
from app.application.read_models import OrderPlacementRepository
from app.domain.orders.events import OrderPaid, OrderPlaced
from app.domain.orders.value_objects import Money, OrderReference


class RecordingPlacements(OrderPlacementRepository):
    """In-memory projection store recording what the projector writes."""

    def __init__(self) -> None:
        self.rows: dict[UUID, OrderPlacement] = {}

    async def add(self, placement: OrderPlacement) -> None:
        self.rows[placement.order_id] = placement

    async def find_one(self, order_id: UUID) -> OrderPlacement | None:
        return self.rows.get(order_id)


def make_order_placed() -> OrderPlaced:
    """Build a domain event the way the aggregate does."""
    return OrderPlaced(
        order_id=uuid4(),
        reference=OrderReference(f"ORD-{uuid4().hex[:8].upper()}").value,
        total=Money(1999).value,
    )


def test_envelope_flattens_a_domain_event() -> None:
    event = make_order_placed()

    envelope = EventEnvelope.from_event(event)

    assert envelope.event_type == OrderPlaced.__name__
    assert envelope.occurred_at == event.occurred_at
    assert envelope.payload[OrderPayloadKey.ORDER_ID] == str(event.order_id)
    assert envelope.payload[OrderPayloadKey.TOTAL] == event.total
    assert isinstance(envelope.payload[OrderPayloadKey.ORDER_ID], str)


def test_envelope_round_trips_through_json() -> None:
    envelope = EventEnvelope.from_event(make_order_placed())
    adapter = TypeAdapter(EventEnvelope)

    assert adapter.validate_json(adapter.dump_json(envelope)) == envelope


def test_to_message_is_json_serializable() -> None:
    import json

    envelope = EventEnvelope.from_event(make_order_placed())

    payload = json.loads(json.dumps(envelope.to_message()))

    assert payload[EnvelopeKey.EVENT_TYPE] == OrderPlaced.__name__
    assert payload[EnvelopeKey.OCCURRED_AT].endswith("+00:00")


def test_jsonify_converts_nested_values() -> None:
    moment = OrderPaid(order_id=uuid4()).occurred_at

    assert jsonify({"id": uuid4(), "at": moment, "nested": [{"at": moment}]})["at"] == moment.isoformat()


async def test_projector_stores_placed_orders() -> None:
    store = RecordingPlacements()
    event = make_order_placed()

    await OrderPlacedProjector(store)(EventEnvelope.from_event(event))

    stored = await store.find_one(event.order_id)
    assert stored is not None
    assert stored.reference == event.reference
    assert stored.total == event.total


async def test_projector_ignores_other_events() -> None:
    store = RecordingPlacements()

    await OrderPlacedProjector(store)(EventEnvelope.from_event(OrderPaid(order_id=uuid4())))

    assert await store.find_one(uuid4()) is None


async def test_projector_is_idempotent() -> None:
    store = RecordingPlacements()
    projector = OrderPlacedProjector(store)
    envelope = EventEnvelope.from_event(make_order_placed())

    await projector(envelope)
    await projector(envelope)

    assert len(store.rows) == 1


@pytest.mark.parametrize("payload", [{}, {"order_id": "not-a-uuid"}, {"order_id": uuid4()}])
async def test_projector_fails_loudly_on_incomplete_payload(payload: dict[str, object]) -> None:
    envelope = EventEnvelope(
        event_type=OrderPlaced.__name__,
        occurred_at=OrderPaid(order_id=uuid4()).occurred_at,
        payload=payload,
    )

    with pytest.raises((KeyError, ValueError)):
        await OrderPlacedProjector(RecordingPlacements())(envelope)
