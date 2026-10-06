"""FastAPI application factory.

``yaddd`` exceptions are translated into HTTP statuses here, once, instead of
being caught route by route: a route that raises ``EntityNotFoundError`` gets a
404 without importing anything from the domain layer's error catalogue.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from starlette.types import ExceptionHandler
from yaddd import (
    BusinessRuleViolationError,
    EntityNotFoundError,
    InfrastructureError,
    InvariantViolationError,
    ValidationError,
    YadddError,
)

from app.composition import Container, build_command_bus, configure_logging
from app.presentation.api.constants import ApiTitle, ErrorPayloadKey
from app.presentation.api.health import build_health_router
from app.presentation.api.orders import build_orders_router


__all__ = ["create_app"]

logger = logging.getLogger(__name__)

NOT_FOUND, CONFLICT, UNPROCESSABLE, UNAVAILABLE, SERVER_ERROR = 404, 409, 422, 503, 500

ERROR_STATUSES: tuple[tuple[type[Exception], int], ...] = (
    (EntityNotFoundError, NOT_FOUND),
    (BusinessRuleViolationError, CONFLICT),
    (InvariantViolationError, CONFLICT),
    (ValidationError, UNPROCESSABLE),
    (PydanticValidationError, UNPROCESSABLE),
    (IntegrityError, CONFLICT),
    (InfrastructureError, UNAVAILABLE),
    (YadddError, SERVER_ERROR),
)


def create_app(container: Container) -> FastAPI:
    """Build the ASGI application of the API process."""
    configure_logging(container.settings)
    bus = build_command_bus(container)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        app.state.container = container
        logger.info("api started: %s on port %s", container.settings.app_name, container.settings.api_port)
        try:
            yield
        finally:
            await container.aclose()
            logger.info("api stopped")

    app = FastAPI(
        title=f"{container.settings.app_name}{ApiTitle.API_SUFFIX}",
        version=ApiTitle.VERSION,
        description=ApiTitle.ORDERS_API_DESCRIPTION,
        lifespan=lifespan,
    )

    for error, code in ERROR_STATUSES:
        app.add_exception_handler(error, _error_handler(code))

    app.include_router(build_health_router(container.probe, container.liveness))
    app.include_router(build_orders_router(bus))
    return app


def _error_handler(code: int) -> ExceptionHandler:
    """Build an exception handler rendering ``code`` for one error type."""

    async def handler(request: Request, exc: Exception) -> JSONResponse:
        logger.warning("%s rejected %s %s: %s", type(exc).__name__, request.method, request.url.path, exc)
        return JSONResponse(
            status_code=code,
            content={ErrorPayloadKey.CODE: type(exc).__name__, ErrorPayloadKey.MESSAGE: str(exc)},
        )

    return handler
