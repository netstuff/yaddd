"""Health endpoints.

Three routes, three questions:

- ``/health`` — what does the process depend on, and what is each answer?
- ``/health/live`` — should the supervisor restart the process?
- ``/health/ready`` — should the load balancer send traffic here?

The routers take probes as arguments: presentation renders a report, it never
computes one.
"""

from fastapi import APIRouter, Response, status

from app.application.health import HealthProbe
from app.presentation.api.constants import ApiPath, ApiSummary, ApiTag
from app.presentation.api.schemas import HealthResponse


__all__ = ["build_health_router"]


def build_health_router(probe: HealthProbe, liveness: HealthProbe) -> APIRouter:
    """Build the health router bound to the given probes."""
    router = APIRouter(tags=[ApiTag.HEALTH])

    @router.get(ApiPath.HEALTH, response_model=HealthResponse, summary=ApiSummary.HEALTH)
    async def health() -> HealthResponse:
        """Return the aggregated readiness report, always with HTTP 200."""
        return HealthResponse.from_report(await probe.report())

    @router.get(ApiPath.HEALTH_LIVE, response_model=HealthResponse, summary=ApiSummary.HEALTH_LIVE)
    async def live() -> HealthResponse:
        """Report the process itself, touching no dependency."""
        return HealthResponse.from_report(await liveness.report())

    @router.get(ApiPath.HEALTH_READY, response_model=HealthResponse, summary=ApiSummary.HEALTH_READY)
    async def ready(response: Response) -> HealthResponse:
        """Report readiness, answering 503 while the process cannot serve traffic."""
        report = await probe.report()
        if not report.ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse.from_report(report)

    return router
