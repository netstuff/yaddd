"""Mappers between domain aggregates and DTOs."""

from yaddd import Mapper

from app.application.dto import OrderDTO
from app.domain.orders.aggregates.order import Order
from app.domain.orders.value_objects import Money, OrderReference


__all__ = ["OrderMapper"]


class OrderMapper(Mapper[OrderDTO, Order]):
    """Translate between ``Order`` and ``OrderDTO``.

    Value objects are unwrapped to primitives here: the DTO contract is
    "flat and serializable", and this is the only place allowed to reach into
    the aggregate's fields.
    """

    def to_dto(self, domain: Order) -> OrderDTO:
        return OrderDTO(
            order_id=domain.id,
            reference=domain.reference.value,
            total=domain.total.value,
            status=domain.status,
        )

    def to_domain(self, dto: OrderDTO) -> Order:
        return Order(
            id=dto.order_id,
            reference=OrderReference(dto.reference),
            total=Money(dto.total),
            status=dto.status,
        )
