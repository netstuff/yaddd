"""SQLAlchemy type decorator persisting ``ValueObject`` instances."""

from typing import Any, ClassVar

from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator
from yaddd.domain.value_object import ValueObject


__all__ = ["VOTypeDecorator"]


class VOTypeDecorator(TypeDecorator[ValueObject[Any]]):
    """Persist a ``ValueObject`` as its raw value and rebuild it on load.

    Subclass, declare ``vo_class`` and pick the storage type via ``impl``::

        class EmailType(VOTypeDecorator):
            impl = String(255)
            cache_ok = True
            vo_class = Email

    Binding unwraps ``value.value``; loading revalidates through
    ``vo_class(value)``. ``None`` passes through untouched in both directions.
    """

    vo_class: ClassVar[type[ValueObject[Any]]]

    def process_bind_param(self, value: ValueObject[Any] | None, dialect: Dialect) -> Any:
        return None if value is None else value.value

    def process_result_value(self, value: Any, dialect: Dialect) -> ValueObject[Any] | None:
        return None if value is None else self.vo_class(value)
