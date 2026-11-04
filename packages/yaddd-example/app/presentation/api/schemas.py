"""HTTP schemas of the orders API.

Request bodies speak in value objects: ``PydanticVO`` validates them with the
same constraints the domain uses, so an invalid reference never reaches a use
case. Responses are built from DTOs and deliberately narrower than the domain —
no card token ever leaves the process through this router.
"""

from pydantic import BaseModel, Field

from app.application.dto import OrderDTO
from app.application.health import HealthReport, ProbeStatus
from app.domain.orders.value_objects import CardToken, Money, OrderReference
from app.presentation.api.constants import OrderFieldDescription


__all__ = [
    "ErrorResponse",
    "HealthResponse",
    "OrderResponse",
    "PlaceOrderRequest",
]


class PlaceOrderRequest(BaseModel):
    """Payload of ``POST /orders``."""

    reference: OrderReference
    total: Money = Field(description=OrderFieldDescription.TOTAL)
    card_token: CardToken | None = None


class OrderResponse(BaseModel):
    """Current state of an order as served over HTTP."""

    order_id: str
    reference: str
    total: int = Field(description=OrderFieldDescription.TOTAL)
    status: str

    @classmethod
    def from_dto(cls, dto: OrderDTO) -> "OrderResponse":
        """Render an application DTO as a response body."""
        return cls(
            order_id=str(dto.order_id),
            reference=dto.reference,
            total=dto.total,
            status=dto.status,
        )


class HealthResponse(BaseModel):
    """Rendered health report."""

    status: ProbeStatus
    ready: bool
    checks: list["HealthCheckResponse"]

    @classmethod
    def from_report(cls, report: HealthReport) -> "HealthResponse":
        """Render an aggregated report as a response body."""
        checks = [
            HealthCheckResponse(name=check.name, status=check.status, detail=check.detail) for check in report.checks
        ]
        return cls(status=report.status, ready=report.ready, checks=checks)


class HealthCheckResponse(BaseModel):
    """Outcome of a single dependency check."""

    name: str
    status: ProbeStatus
    detail: str | None = None


class ErrorResponse(BaseModel):
    """Uniform error body for every handler of this API."""

    code: str
    message: str
