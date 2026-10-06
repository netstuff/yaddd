"""Worker CLI and ASGI constants."""

__all__ = [
    "PlaceOrderArg",
    "WorkerCliKey",
    "WorkerCommand",
    "WorkerError",
    "WorkerLogMessage",
    "WorkerPath",
    "WorkerTitle",
]


class WorkerCommand:
    """Subcommands of the worker CLI."""

    MIGRATE = "migrate"
    DROP_ALL = "drop-all"
    HEALTH = "health"
    PLACE_ORDER = "place-order"
    CONSUME = "consume"
    DRAIN = "drain"


class WorkerCliKey:
    """Argument parser metadata."""

    PROG = "worker"
    DESCRIPTION = "Operator commands of the worker."


class WorkerPath:
    """Probe and document paths of the worker ASGI app."""

    HEALTH = "/health"
    HEALTH_LIVE = "/health/live"
    HEALTH_READY = "/health/ready"
    ASYNCAPI = "/docs/asyncapi"
    ASYNCAPI_JSON = "/docs/asyncapi.json"


class WorkerTitle:
    """Metadata of the worker AsyncAPI document."""

    VERSION = "0.1.0"
    DESCRIPTION = "Domain event consumers of this worker."


class PlaceOrderArg:
    """Arguments of the ``place-order`` CLI command."""

    REFERENCE = "--reference"
    TOTAL = "--total"
    CARD_TOKEN = "--card-token"
    REFERENCE_HELP = "Order reference, e.g. ORD-1A2B3C4D."
    CARD_TOKEN_HELP = "Opaque payment token."


class WorkerLogMessage:
    """Log messages emitted by the worker CLI."""

    SCHEMA_UP_TO_DATE = "schema is up to date"
    TABLES_DROPPED = "all tables dropped"
    CONSUMING = "consuming events from %s, press Ctrl+C to stop"
    COLLECTED = "collected %s event(s)"


class WorkerError:
    """Error messages of the worker CLI."""

    DUPLICATE_UNIQUE_VALUE = "a record with the same unique value already exists"
    STDERR_PREFIX = "error:"
