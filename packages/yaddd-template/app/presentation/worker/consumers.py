"""Subscriber wiring of the worker process.

FastStream consumers are registered here and nowhere else: the broker is
infrastructure, the projection is application, and only the entrypoint knows
that a Redis channel feeds one projector.
"""

from collections.abc import Awaitable, Callable

from faststream.redis import RedisBroker

from app.application.messaging import EventEnvelope
from app.application.projections import OrderPlacedProjector


__all__ = ["make_event_handler", "register_consumers"]


def register_consumers(broker: RedisBroker, projector: OrderPlacedProjector, channel: str) -> None:
    """Attach every consumer of this process to the given broker."""
    broker.subscriber(channel)(make_event_handler(projector))


Projector = Callable[[EventEnvelope], Awaitable[None]]


def make_event_handler(projector: Projector) -> Projector:
    """Adapt a projector to the subscriber signature FastStream expects.

    The ``EventEnvelope`` annotation is not decoration: FastStream validates and
    decodes every incoming message against it, so a malformed payload is
    rejected before it reaches the projector.
    """

    async def handle_event(event: EventEnvelope) -> None:
        await projector(event)

    return handle_event
