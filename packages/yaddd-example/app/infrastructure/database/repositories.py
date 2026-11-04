"""SQLAlchemy Core implementation of the order repository port."""

from typing import Any

from sqlalchemy.engine import Row
from yaddd_sqlalchemy import SqlTransactionBoundRepository

from app.domain.orders.aggregates.order import Order
from app.infrastructure.database.constants import OrderColumn
from app.infrastructure.database.models import orders_table


__all__ = ["SqlOrderRepository"]


class SqlOrderRepository(SqlTransactionBoundRepository[Order]):
    """Maps ``orders`` rows onto ``Order`` aggregates.

    Extending ``SqlTransactionBoundRepository`` instead of the plain
    ``SqlCrudRepository`` is what makes events work: every ``create`` and
    ``update`` registers the aggregate on the transaction, so the unit of work
    publishes its domain events right after a successful commit.

    The session is resolved lazily from the transaction, so the repository may
    be constructed before the ``async with`` block is entered.
    """

    table = orders_table

    def to_domain(self, row: Row[Any]) -> Order:
        return Order(
            id=row.id,
            reference=row.reference,
            total=row.total,
            status=row.status,
            card_token=row.card_token,
        )

    def to_row(self, instance: Order) -> dict[str, Any]:
        return {
            OrderColumn.ID: instance.id,
            OrderColumn.REFERENCE: instance.reference,
            OrderColumn.TOTAL: instance.total,
            OrderColumn.STATUS: instance.status,
            OrderColumn.CARD_TOKEN: instance.card_token,
        }
