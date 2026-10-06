"""Repository ports of the orders slice.

The domain states *what* persistence it needs; ``infrastructure`` decides *how*
it is satisfied. ``yaddd-sqlalchemy`` implements this port over SQLAlchemy
Core without any ORM declarative opinions.
"""

from yaddd import CrudRepository

from app.domain.orders.aggregates.order import Order


__all__ = ["OrderRepository"]


type OrderRepository = CrudRepository[Order]
