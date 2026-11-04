"""SQLAlchemy Core store for the order placement projection."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.dto import OrderPlacement
from app.infrastructure.database.constants import OrderPlacementColumn
from app.infrastructure.database.models import order_placements_table


__all__ = ["SqlOrderPlacementRepository"]


class SqlOrderPlacementRepository:
    """Append-only store of placed orders, written by the broker consumer.

    This repository commits on its own instead of joining a caller's unit of
    work: it is fed by messages, which already crossed a process boundary, so
    there is no surrounding business transaction to join.
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def add(self, placement: OrderPlacement) -> None:
        """Append a placement row."""
        async with self._session_maker.begin() as session:
            await session.execute(
                insert(order_placements_table).values(
                    **{
                        OrderPlacementColumn.ORDER_ID: placement.order_id,
                        OrderPlacementColumn.REFERENCE: placement.reference,
                        OrderPlacementColumn.TOTAL: placement.total,
                        OrderPlacementColumn.PLACED_AT: placement.placed_at,
                    }
                )
            )

    async def find_one(self, order_id: UUID) -> OrderPlacement | None:
        """Return the placement recorded for ``order_id``, if any."""
        async with self._session_maker() as session:
            row = (
                await session.execute(
                    select(order_placements_table).where(order_placements_table.c.order_id == order_id)
                )
            ).first()

        if row is None:
            return None

        return OrderPlacement(
            order_id=row.order_id,
            reference=row.reference,
            total=row.total,
            placed_at=_as_utc(row.placed_at),
        )


def _as_utc(value: datetime) -> datetime:
    """Restore the UTC offset that SQLite drops when storing datetimes."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
