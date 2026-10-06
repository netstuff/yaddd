"""Wire format of the domain event stream.

The unit of work publishes events only after a successful commit, but the
publisher is an infrastructure port: it must turn framework objects into
something a broker can carry. That translation happens here, in the
application layer, so both the producer (``infrastructure.messaging``) and the
consumer (``presentation.worker``) agree on one shape without either of them
importing the other.

The envelope is deliberately dumb: an event name, the moment it happened and a
JSON-safe payload. Rebuilding domain events from it is a consumer decision,
never the transport's.
"""

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from yaddd import DomainEvent


if TYPE_CHECKING:
    from _typeshed import DataclassInstance


__all__ = ["EnvelopeKey", "EventEnvelope"]


class EnvelopeKey:
    """Wire keys of an :class:`EventEnvelope`."""

    EVENT_TYPE = "event_type"
    OCCURRED_AT = "occurred_at"
    PAYLOAD = "payload"


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """A domain event flattened into a broker-friendly record.

    Attributes:
        event_type: Class name of the originating event, e.g. ``OrderPlaced``.
        occurred_at: When the fact happened, not when it was published.
        payload: Event fields with every value converted to a JSON primitive.
    """

    event_type: str
    occurred_at: datetime
    payload: dict[str, Any]

    @classmethod
    def from_event(cls, event: DomainEvent) -> "EventEnvelope":
        """Flatten a domain event into a transport-ready envelope."""
        fields = asdict(cast("DataclassInstance", event))
        occurred_at: datetime = fields.pop(EnvelopeKey.OCCURRED_AT)
        return cls(event_type=type(event).__name__, occurred_at=occurred_at, payload=jsonify(fields))

    def to_message(self) -> dict[str, Any]:
        """Return the JSON-ready mapping a broker publishes."""
        return {
            EnvelopeKey.EVENT_TYPE: self.event_type,
            EnvelopeKey.OCCURRED_AT: self.occurred_at.isoformat(),
            EnvelopeKey.PAYLOAD: self.payload,
        }


def jsonify(value: Any) -> Any:
    """Convert dataclass payloads into values ``json.dumps`` accepts."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        mapping = cast("Mapping[Any, Any]", value)
        return {str(key): jsonify(item) for key, item in mapping.items()}
    if isinstance(value, list | tuple | set | frozenset):
        items = cast("Iterable[Any]", value)
        return [jsonify(item) for item in items]
    return value
