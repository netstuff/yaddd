"""Transactional boundary of the orders slice."""

from dataclasses import dataclass

from yaddd import UnitOfWork

from app.domain.orders.repositories import OrderRepository


__all__ = ["OrderRepositories", "OrderUnitOfWork"]


@dataclass(frozen=True, slots=True)
class OrderRepositories:
    """Repository bundle shared by everything inside one unit of work.

    Repositories handed out here share a single SQLAlchemy session and a
    single transaction: they must never be cached across units of work.
    """

    orders: OrderRepository


type OrderUnitOfWork = UnitOfWork[OrderRepositories]
