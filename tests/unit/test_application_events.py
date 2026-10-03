from yaddd.application import InMemoryEventPublisher
from yaddd.domain import DomainEvent


class OrderPlaced(DomainEvent):
    pass


class OrderShipped(DomainEvent):
    pass


class Collector:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def __call__(self, event: DomainEvent) -> None:
        self.events.append(event)


async def test_publish_dispatches_to_subscribed_handler():
    collector = Collector()
    publisher = InMemoryEventPublisher()
    publisher.subscribe(OrderPlaced, collector)

    event = OrderPlaced()
    await publisher.publish([event])

    assert collector.events == [event]


async def test_publish_skips_unsubscribed_event_types():
    collector = Collector()
    publisher = InMemoryEventPublisher()
    publisher.subscribe(OrderPlaced, collector)

    await publisher.publish([OrderShipped()])

    assert collector.events == []


async def test_base_type_subscription_receives_subtypes():
    collector = Collector()
    publisher = InMemoryEventPublisher()
    publisher.subscribe(DomainEvent, collector)

    await publisher.publish([OrderPlaced(), OrderShipped()])

    assert len(collector.events) == 2


async def test_publish_without_subscribers_is_noop():
    publisher = InMemoryEventPublisher()
    await publisher.publish([OrderPlaced()])


async def test_handlers_called_in_subscription_order():
    calls: list[str] = []
    publisher = InMemoryEventPublisher()

    async def first(_event: DomainEvent) -> None:
        calls.append("first")

    async def second(_event: DomainEvent) -> None:
        calls.append("second")

    publisher.subscribe(OrderPlaced, first)
    publisher.subscribe(OrderPlaced, second)
    await publisher.publish([OrderPlaced()])

    assert calls == ["first", "second"]
