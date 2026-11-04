"""Database schema identifiers."""

__all__ = ["OrderColumn", "OrderPlacementColumn", "Query", "TableName"]


class TableName:
    """SQLAlchemy table names."""

    ORDERS = "orders"
    ORDER_PLACEMENTS = "order_placements"


class OrderColumn:
    """Column names of the ``orders`` table."""

    ID = "id"
    REFERENCE = "reference"
    TOTAL = "total"
    STATUS = "status"
    CARD_TOKEN = "card_token"


class OrderPlacementColumn:
    """Column names of the ``order_placements`` table."""

    ORDER_ID = "order_id"
    REFERENCE = "reference"
    TOTAL = "total"
    PLACED_AT = "placed_at"


class Query:
    """Raw SQL snippets used by adapters."""

    HEALTH_CHECK = "SELECT 1"
