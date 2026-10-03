from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from yaddd.application import DTO, ApplicationService, Command, Mapper
from yaddd.domain import AggregateRoot


class OrderDTO(DTO):
    order_id: str
    total: int


class Order(AggregateRoot):
    id: UUID
    total: int


class OrderMapper:
    def to_dto(self, domain: Order) -> OrderDTO:
        return OrderDTO(order_id=str(domain.pk), total=domain.total)

    def to_domain(self, dto: OrderDTO) -> Order:
        return Order(id=UUID(dto.order_id), total=dto.total)


class PlaceOrder(Command):
    order_id: UUID
    total: int


class PlaceOrderService(ApplicationService[PlaceOrder, OrderDTO]):
    def __init__(self, mapper: Mapper[OrderDTO, Order]) -> None:
        self._mapper = mapper

    async def execute(self, command: PlaceOrder) -> OrderDTO:
        order = Order(id=command.order_id, total=command.total)
        return self._mapper.to_dto(order)


def test_dto_is_frozen_and_kw_only():
    dto = OrderDTO(order_id="x", total=10)
    with pytest.raises(FrozenInstanceError):
        dto.total = 20  # type: ignore[misc]
    with pytest.raises(TypeError):
        OrderDTO("x", 10)  # type: ignore[misc]


def test_mapper_round_trip():
    mapper: Mapper[OrderDTO, Order] = OrderMapper()
    order = Order(id=uuid4(), total=10)
    dto = mapper.to_dto(order)

    assert dto == OrderDTO(order_id=str(order.pk), total=10)
    assert mapper.to_domain(dto) == order


async def test_application_service_call_delegates_to_execute():
    service = PlaceOrderService(OrderMapper())
    order_id = uuid4()

    dto = await service(PlaceOrder(order_id=order_id, total=10))

    assert dto == OrderDTO(order_id=str(order_id), total=10)
