"""HTTP API constants."""

__all__ = [
    "ApiPath",
    "ApiSummary",
    "ApiTag",
    "ApiTitle",
    "ErrorPayloadKey",
    "OrderFieldDescription",
    "OrderPathParam",
    "UvicornTarget",
]


class OrderFieldDescription:
    """Human-readable descriptions of order fields."""

    TOTAL = "Amount in minor currency units"


class ApiTag:
    """OpenAPI tags of the API routes."""

    HEALTH = "health"
    ORDERS = "orders"


class ApiPath:
    """Paths of the HTTP routes."""

    ORDERS_PREFIX = "/orders"
    HEALTH = "/health"
    HEALTH_LIVE = "/health/live"
    HEALTH_READY = "/health/ready"
    OPENAPI = "/openapi.json"


class ApiTitle:
    """Metadata of the API document."""

    VERSION = "0.1.0"
    ORDERS_API_DESCRIPTION = "Orders API generated from a yaddd-domain skeleton."
    API_SUFFIX = " API"


class ErrorPayloadKey:
    """Keys of the uniform error body."""

    CODE = "code"
    MESSAGE = "message"


class OrderPathParam:
    """Path parameter of the orders router."""

    ORDER_ID = "order_id"
    DESCRIPTION = "Order identifier"


class ApiSummary:
    """Route summaries of the API."""

    PLACE_ORDER = "Place an order"
    PAY_ORDER = "Settle an order"
    HEALTH = "Report every dependency check"
    HEALTH_LIVE = "Liveness probe"
    HEALTH_READY = "Readiness probe"


class UvicornTarget:
    """Uvicorn import path of the API ASGI app."""

    API_APP = "app.presentation.api.asgi:app"
