"""Domain event publisher over a message broker."""

import logging
from collections.abc import Sequence

from faststream.redis import RedisBroker
from yaddd import DomainEvent

from app.application.dto import OrderPayloadKey
from app.application.messaging import EventEnvelope


__all__ = ["BrokerEventPublisher"]

logger = logging.getLogger(__name__)


class BrokerEventPublisher:
    """Publishes domain events to a Redis channel.

    ``yaddd`` calls this only after a successful commit, so a failure here
    means "the order is saved, the announcement is not" — the log line below is
    what an operator greps for when reconciling projections. It never raises a
    business error into the use case: the use case already succeeded.
    """

    def __init__(self, broker: RedisBroker, channel: str) -> None:
        self._broker = broker
        self._channel = channel

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        """Publish every event of one committed unit of work."""
        for event in events:
            envelope = EventEnvelope.from_event(event)
            try:
                await self._broker.publish(envelope.to_message(), channel=self._channel)
            except Exception:
                logger.exception("failed to publish %s to channel %s", envelope.event_type, self._channel)
            else:
                logger.info(
                    "published %s for %s",
                    envelope.event_type,
                    envelope.payload.get(OrderPayloadKey.ORDER_ID, "-"),
                )
