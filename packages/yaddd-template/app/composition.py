"""Composition root — the only module allowed to import every layer.

Every concrete dependency is chosen here and nowhere else: which database
engine, which broker, which repository implementation, which probe. Layers
below stay ignorant of each other, which is exactly why this file is allowed to
be the ugly one.

Container fields are built once per process; units of work are built per
operation by ``make_uow``.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from faststream.redis import RedisBroker
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from yaddd import Command, CommandBus, HandlerNotFoundError

from app.application.commands import MarkOrderPaid, PlaceOrder
from app.application.dto import OrderDTO
from app.application.handlers import MarkOrderPaidHandler, PlaceOrderHandler
from app.application.health import HealthProbe
from app.application.mappers import OrderMapper
from app.application.projections import OrderPlacedProjector
from app.application.read_models import OrderPlacementRepository
from app.application.uow import OrderUnitOfWork
from app.infrastructure.config.constants import ProcessSuffix
from app.infrastructure.config.logging import configure_logging
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.database.read_models import SqlOrderPlacementRepository
from app.infrastructure.database.uow import create_schema, drop_schema, make_uow_factory
from app.infrastructure.health import BrokerCheck, CompositeHealthProbe, DatabaseCheck, LivenessProbe
from app.infrastructure.messaging.broker import make_broker
from app.infrastructure.messaging.publisher import BrokerEventPublisher


__all__ = [
    "Container",
    "build_command_bus",
    "build_container",
    "configure_logging",
    "create_schema",
    "drop_schema",
    "get_settings",
]


@dataclass(frozen=True, slots=True)
class Container:
    """Every dependency a process needs, already wired together."""

    settings: Settings
    engine: AsyncEngine
    session_maker: async_sessionmaker[AsyncSession]
    broker: RedisBroker
    publisher: BrokerEventPublisher
    make_uow: Callable[[], OrderUnitOfWork]
    mapper: OrderMapper
    placements: OrderPlacementRepository
    projector: OrderPlacedProjector
    probe: HealthProbe
    liveness: HealthProbe

    async def aclose(self) -> None:
        """Release pooled connections held by this process."""
        await self.engine.dispose()


def build_container(settings: Settings | None = None) -> Container:
    """Wire the object graph described by ``settings``."""
    resolved = settings or get_settings()

    engine = create_async_engine(resolved.database_url, echo=resolved.db_echo, future=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    broker = make_broker(resolved.broker_url)
    publisher = BrokerEventPublisher(broker, resolved.broker_events_channel)
    placements = SqlOrderPlacementRepository(session_maker)

    return Container(
        settings=resolved,
        engine=engine,
        session_maker=session_maker,
        broker=broker,
        publisher=publisher,
        make_uow=make_uow_factory(session_maker, publisher),
        mapper=OrderMapper(),
        placements=placements,
        projector=OrderPlacedProjector(placements),
        probe=CompositeHealthProbe(
            checks=(
                DatabaseCheck(session_maker, resolved.probe_timeout),
                BrokerCheck(broker, resolved.probe_timeout),
            ),
            timeout=resolved.probe_timeout,
        ),
        liveness=LivenessProbe(f"{resolved.app_name}{ProcessSuffix.API}"),
    )


def build_command_bus(container: Container) -> CommandBus[Command, OrderDTO]:
    """Bind every command to a handler that opens its own unit of work.

    The bus holds callables, not handler instances: a handler owns a unit of
    work, and a unit of work must never outlive one request. Each dispatch
    therefore builds a fresh handler with a fresh unit of work, which is what
    keeps concurrent requests from interleaving transactions on one connection.
    """
    bus: CommandBus[Command, OrderDTO] = CommandBus()

    def place_order(command: Command) -> Awaitable[OrderDTO]:
        return PlaceOrderHandler(container.make_uow(), container.mapper)(_narrow(command, PlaceOrder))

    def mark_paid(command: Command) -> Awaitable[OrderDTO]:
        return MarkOrderPaidHandler(container.make_uow(), container.mapper)(_narrow(command, MarkOrderPaid))

    bus.register(PlaceOrder, place_order)
    bus.register(MarkOrderPaid, mark_paid)
    return bus


def _narrow[C: Command](command: Command, expected: type[C]) -> C:
    """Narrow a bus message to the command its handler expects."""
    if not isinstance(command, expected):
        raise HandlerNotFoundError(f"No handler registered for {type(command).__name__}")
    return command
