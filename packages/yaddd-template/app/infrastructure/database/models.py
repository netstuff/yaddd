"""The SQLAlchemy Core schema.

No ORM declarative base: ``yaddd-sqlalchemy`` is Core-only, so tables are
declared explicitly and aggregates are mapped by hand in
``infrastructure.database.repositories``.

Value objects get a dedicated column type through ``VOTypeDecorator``: the raw
value is written to the database and the instance is rebuilt — and therefore
revalidated — on load.
"""

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Uuid
from yaddd_sqlalchemy import VOTypeDecorator

from app.domain.orders.value_objects import CardToken, Money, OrderReference
from app.infrastructure.database.constants import OrderColumn, OrderPlacementColumn, TableName


__all__ = ["metadata", "order_placements_table", "orders_table"]


class OrderReferenceType(VOTypeDecorator):
    """Stores an ``OrderReference`` as its raw string."""

    impl = String(16)
    cache_ok = True
    vo_class = OrderReference


class MoneyType(VOTypeDecorator):
    """Stores a ``Money`` as minor currency units."""

    impl = Integer()
    cache_ok = True
    vo_class = Money


class CardTokenType(VOTypeDecorator):
    """Stores a ``CardToken`` as an opaque string."""

    impl = String(64)
    cache_ok = True
    vo_class = CardToken


metadata = MetaData()

orders_table = Table(
    TableName.ORDERS,
    metadata,
    Column(OrderColumn.ID, Uuid(), primary_key=True),
    Column(OrderColumn.REFERENCE, OrderReferenceType(), nullable=False, unique=True),
    Column(OrderColumn.TOTAL, MoneyType(), nullable=False),
    Column(OrderColumn.STATUS, String(32), nullable=False),
    Column(OrderColumn.CARD_TOKEN, CardTokenType(), nullable=True),
)

order_placements_table = Table(
    TableName.ORDER_PLACEMENTS,
    metadata,
    Column(OrderPlacementColumn.ORDER_ID, Uuid(), primary_key=True),
    Column(OrderPlacementColumn.REFERENCE, String(16), nullable=False),
    Column(OrderPlacementColumn.TOTAL, Integer(), nullable=False),
    Column(OrderPlacementColumn.PLACED_AT, DateTime(timezone=True), nullable=False),
)
