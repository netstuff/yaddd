"""ASGI entrypoint of the worker process.

The worker is a server, not a script: it consumes domain events *and* answers
probes, so Kubernetes can tell "slow consumer" apart from "dead process".
Liveness stays dependency-free, readiness reports the database and the broker.
"""

from collections.abc import Sequence

import uvicorn
from faststream import AsyncAPI
from faststream.asgi import AsgiFastStream, get
from faststream.asgi.factories.asyncapi.route import AsyncAPIRoute
from faststream.asgi.response import AsgiResponse, JSONResponse
from faststream.asgi.types import ASGIApp, Scope

from app.composition import Container, build_container, configure_logging, get_settings
from app.presentation.worker.constants import WorkerPath, WorkerTitle
from app.presentation.worker.consumers import register_consumers


__all__ = ["build_worker_app", "main"]


def build_probe_routes(container: Container) -> Sequence[tuple[str, ASGIApp]]:
    """Build the probe routes served next to the consumers."""

    @get(description="Report every dependency check")
    async def health(scope: Scope) -> AsgiResponse:
        report = await container.probe.report()
        return JSONResponse(report.to_payload(), status_code=200 if report.ready else 503)

    @get(description="Liveness probe")
    async def live(scope: Scope) -> AsgiResponse:
        report = await container.liveness.report()
        return JSONResponse(report.to_payload(), status_code=200)

    @get(description="Readiness probe")
    async def ready(scope: Scope) -> AsgiResponse:
        report = await container.probe.report()
        return JSONResponse(report.to_payload(), status_code=200 if report.ready else 503)

    return ((WorkerPath.HEALTH, health), (WorkerPath.HEALTH_LIVE, live), (WorkerPath.HEALTH_READY, ready))


def build_worker_app(container: Container) -> AsgiFastStream:
    """Build the ASGI application of the worker process."""
    configure_logging(container.settings)
    register_consumers(container.broker, container.projector, container.settings.broker_events_channel)

    return AsgiFastStream(
        container.broker,
        asgi_routes=build_probe_routes(container),
        specification=AsyncAPI(
            container.broker,
            title=f"{container.settings.app_name} events",
            version=WorkerTitle.VERSION,
            description=WorkerTitle.DESCRIPTION,
        ),
        asyncapi_path=AsyncAPIRoute(path=WorkerPath.ASYNCAPI, description="AsyncAPI document of the worker"),
    )


def main() -> None:
    """Serve the worker with uvicorn."""
    settings = get_settings()
    uvicorn.run(
        build_worker_app(build_container()),
        host=settings.worker_host,
        port=settings.worker_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
