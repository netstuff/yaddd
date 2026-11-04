"""Order endpoints.

The router holds no business logic: it validates the request, dispatches a
command through the bus and renders the resulting DTO. Every failure mode is
mapped to a status code once, in the application factory, so routes stay free
of try/except.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, status
from yaddd import Command, CommandBus

from app.application.commands import MarkOrderPaid, PlaceOrder
from app.application.dto import OrderDTO
from app.presentation.api.constants import ApiPath, ApiSummary, ApiTag, OrderPathParam
from app.presentation.api.schemas import OrderResponse, PlaceOrderRequest


__all__ = ["build_orders_router"]


def build_orders_router(bus: CommandBus[Command, OrderDTO]) -> APIRouter:
    """Build the orders router bound to the given command bus."""
    router = APIRouter(prefix=ApiPath.ORDERS_PREFIX, tags=[ApiTag.ORDERS])

    @router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary=ApiSummary.PLACE_ORDER)
    async def place_order(payload: PlaceOrderRequest) -> OrderResponse:
        """Register a new order and accept it."""
        dto = await bus.dispatch(
            PlaceOrder(
                reference=payload.reference.value,
                total=payload.total.value,
                card_token=payload.card_token.value if payload.card_token is not None else None,
            )
        )
        return OrderResponse.from_dto(dto)

    @router.post(f"/{{{OrderPathParam.ORDER_ID}}}/pay", response_model=OrderResponse, summary=ApiSummary.PAY_ORDER)
    async def mark_paid(
        order_id: Annotated[UUID, Path(description=OrderPathParam.DESCRIPTION)],
    ) -> OrderResponse:
        """Settle a placed order; 409 while it is not placed yet."""
        return OrderResponse.from_dto(await bus.dispatch(MarkOrderPaid(order_id=order_id)))

    return router
