"""Read the domain event channel straight from Redis.

An escape hatch for operators: when a projection looks wrong, the first question
is whether the events themselves were published. This reads the channel without
running a consumer, so it changes nothing.
"""

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any, cast

from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from redis.exceptions import RedisError

from app.application.messaging import EventEnvelope
from app.shared.constants import Encoding


__all__ = ["drain_events"]

logger = logging.getLogger(__name__)

_ENVELOPE = TypeAdapter(EventEnvelope)


async def drain_events(url: str, channel: str, timeout: float) -> list[EventEnvelope]:
    """Collect messages published to ``channel`` within ``timeout`` seconds.

    Args:
        url: Redis connection URL.
        channel: Pub/sub channel carrying domain events.
        timeout: How long to listen before returning what arrived.

    Returns:
        Every decoded event, in arrival order; empty if the channel is idle.
    """
    factory = cast("Callable[..., Redis]", Redis.from_url)
    client: Redis = factory(url)
    collected: list[EventEnvelope] = []

    try:
        pubsub: PubSub = client.pubsub()
        async with pubsub:
            await pubsub.subscribe(channel)
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout

            while loop.time() < deadline:
                message = cast(
                    "Mapping[str, Any] | None",
                    await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5),
                )
                envelope = decode_payload(message["data"] if message else None)
                if envelope is not None:
                    collected.append(envelope)
    except RedisError:
        logger.exception("failed to drain channel %s", channel)
    finally:
        await client.aclose()

    return collected


def decode_payload(data: object) -> EventEnvelope | None:
    """Validate one raw pub/sub payload into an envelope."""
    if not isinstance(data, bytes | str):
        return None

    raw = data.decode(Encoding.UTF8, "replace") if isinstance(data, bytes) else data
    try:
        return _ENVELOPE.validate_json(raw)
    except ValidationError:
        logger.warning("skipping malformed event payload: %r", raw[:200])
        return None
