"""Operator CLI of the worker process.

The CLI implements ``yaddd.CliCommand``: it parses arguments, runs exactly one
use case and returns an exit code. It owns its event loop through
``asyncio.run`` because application services are async, and it never touches
domain or infrastructure internals — everything arrives through the container.
"""

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from yaddd import CliCommand, YadddError

from app.application.commands import PlaceOrder
from app.application.dto import OrderDTO, OrderPayloadKey
from app.application.health import HealthReport
from app.composition import (
    Container,
    build_command_bus,
    build_container,
    configure_logging,
    create_schema,
    drop_schema,
)
from app.presentation.api.constants import OrderFieldDescription
from app.presentation.worker.constants import (
    PlaceOrderArg,
    WorkerCliKey,
    WorkerCommand,
    WorkerError,
    WorkerLogMessage,
)
from app.presentation.worker.consumers import register_consumers
from app.presentation.worker.drain import drain_events


__all__ = ["WorkerCli", "build_parser", "main"]

logger = logging.getLogger(__name__)

type CommandHandler = Callable[[argparse.Namespace, Container], Coroutine[Any, Any, int]]


class WorkerCli(CliCommand):
    """Entrypoint behind ``worker``."""

    def __init__(self, container: Container | None = None) -> None:
        self._container = container

    def run(self, args: Sequence[str]) -> int:
        """Run one command and return its process exit code.

        Expected failures — a business rule, invalid input, a constraint
        violation — become one line on stderr and exit code 1, the same way the
        HTTP edge turns them into 4xx. Anything else propagates: an unexpected
        crash deserves its traceback.
        """
        parsed = build_parser().parse_args(args)
        container = self._container or build_container()
        configure_logging(container.settings)

        handlers: dict[str, CommandHandler] = {
            WorkerCommand.MIGRATE: self._migrate,
            WorkerCommand.DROP_ALL: self._drop_all,
            WorkerCommand.HEALTH: self._health,
            WorkerCommand.PLACE_ORDER: self._place_order,
            WorkerCommand.CONSUME: self._consume,
            WorkerCommand.DRAIN: self._drain,
        }
        try:
            return asyncio.run(handlers[parsed.command](parsed, container))
        except (YadddError, PydanticValidationError, IntegrityError) as exc:
            print(f"{WorkerError.STDERR_PREFIX} {_explain(exc)}", file=sys.stderr)
            return 1

    async def _migrate(self, args: argparse.Namespace, container: Container) -> int:
        """Create every table declared in the metadata."""
        await create_schema(container.engine)
        logger.info(WorkerLogMessage.SCHEMA_UP_TO_DATE)
        return 0

    async def _drop_all(self, args: argparse.Namespace, container: Container) -> int:
        """Drop every table — a development convenience, never a deployment step."""
        await drop_schema(container.engine)
        logger.warning(WorkerLogMessage.TABLES_DROPPED)
        return 0

    async def _health(self, args: argparse.Namespace, container: Container) -> int:
        """Print the health report and fail when the process is not ready."""
        report: HealthReport = await container.probe.report()
        print(json.dumps(report.to_payload(), indent=2))
        return 0 if report.ready else 1

    async def _place_order(self, args: argparse.Namespace, container: Container) -> int:
        """Place an order without going through HTTP."""
        dto: OrderDTO = await build_command_bus(container).dispatch(
            PlaceOrder(reference=args.reference, total=args.total, card_token=args.card_token)
        )
        print(json.dumps(_dto_payload(dto), indent=2))
        return 0

    async def _consume(self, args: argparse.Namespace, container: Container) -> int:
        """Run consumers in the foreground, without serving probes."""
        register_consumers(container.broker, container.projector, container.settings.broker_events_channel)
        async with container.broker:
            logger.info(WorkerLogMessage.CONSUMING, container.settings.broker_events_channel)
            await asyncio.Event().wait()
        return 0

    async def _drain(self, args: argparse.Namespace, container: Container) -> int:
        """Print events observed on the channel without consuming them."""
        settings = container.settings
        events = await drain_events(settings.broker_url, settings.broker_events_channel, args.seconds)
        for event in events:
            print(json.dumps(event.to_message(), indent=2))
        logger.info(WorkerLogMessage.COLLECTED, len(events))
        return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser of ``worker``."""
    parser = argparse.ArgumentParser(prog=WorkerCliKey.PROG, description=WorkerCliKey.DESCRIPTION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(WorkerCommand.MIGRATE, help="Create missing tables.")
    subparsers.add_parser(WorkerCommand.DROP_ALL, help="Drop all tables (development only).")
    subparsers.add_parser(WorkerCommand.HEALTH, help="Print the health report; exit 1 when not ready.")
    subparsers.add_parser(WorkerCommand.CONSUME, help="Consume domain events in the foreground.")

    place_order = subparsers.add_parser(WorkerCommand.PLACE_ORDER, help="Place an order without HTTP.")
    place_order.add_argument(PlaceOrderArg.REFERENCE, required=True, help=PlaceOrderArg.REFERENCE_HELP)
    place_order.add_argument(PlaceOrderArg.TOTAL, required=True, type=int, help=OrderFieldDescription.TOTAL)
    place_order.add_argument(PlaceOrderArg.CARD_TOKEN, default=None, help=PlaceOrderArg.CARD_TOKEN_HELP)

    drain = subparsers.add_parser(WorkerCommand.DRAIN, help="Print events published on the channel.")
    drain.add_argument("--seconds", type=float, default=5.0, help="How long to listen.")

    return parser


def _explain(exc: Exception) -> str:
    """Render an expected failure for an operator, never as a SQL dump."""
    if isinstance(exc, IntegrityError):
        return WorkerError.DUPLICATE_UNIQUE_VALUE
    return str(exc)


def _dto_payload(dto: OrderDTO) -> dict[str, Any]:
    """Render an order DTO as a JSON-ready mapping."""
    return {
        OrderPayloadKey.ORDER_ID: str(dto.order_id),
        OrderPayloadKey.REFERENCE: dto.reference,
        OrderPayloadKey.TOTAL: dto.total,
        OrderPayloadKey.STATUS: dto.status,
    }


def main() -> None:
    """Entry point of the ``worker`` script."""
    raise SystemExit(WorkerCli().run(sys.argv[1:]))


if __name__ == "__main__":
    main()
