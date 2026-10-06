"""Redis broker wiring.

The broker object itself is infrastructure: it knows about URLs and Redis. How
subscribers are attached to it is a presentation decision, so this module stops
at ``make_broker``.
"""

from faststream.redis import RedisBroker


__all__ = ["make_broker"]


def make_broker(url: str) -> RedisBroker:
    """Create a Redis pub/sub broker.

    Redis pub/sub is the right first choice for domain events: the broker needs
    no durability of its own, because the outbox pattern (state committed
    first, event published afterwards) already makes redelivery the caller's
    problem to handle. Swap this function for a Kafka or NATS implementation and
    nothing above it changes.
    """
    return RedisBroker(url=url)
