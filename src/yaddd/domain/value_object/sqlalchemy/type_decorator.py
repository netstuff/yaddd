"""SQLAlchemy integration with ValueObject."""

from typing import Any, Protocol, Type, TypeVar, overload

from sqlalchemy import Dialect, String, TypeDecorator
from sqlalchemy.sql.type_api import TypeEngine

from ..base import ValueObject


_PythonValueT = TypeVar("_PythonValueT")
_StorableValueT = TypeVar("_StorableValueT")


class _ConverterProtocol(Protocol):
    """Protocol for converting values between Python and database storage."""

    @overload
    def __call__(self, value: _PythonValueT, dialect: Dialect) -> _StorableValueT | None: ...

    @overload
    def __call__(self, value: _StorableValueT, dialect: Dialect) -> _PythonValueT | None: ...

    def __call__(self, value: Any, dialect: Dialect) -> Any: ...


def create_type_decorator(
    value_type: Type[ValueObject] | Type | None = None,
    sql_type: TypeEngine = String,
    serialize: _ConverterProtocol | None = None,
    deserialize: _ConverterProtocol | None = None,
    *,
    cacheable: bool = True,
    type_name: str | None = None,
) -> Type[TypeDecorator]:
    """
    Factory for creating custom SQLAlchemy TypeDecorator for ValueObject.

    Args:
        value_type: ValueObject type for automatic conversion
        sql_type: Base SQLAlchemy storage type (default: String)
        serialize: Custom serialization function to database format
        deserialize: Custom deserialization function from database format
        cacheable: Indicates if this TypeDecorator is safe to be used as part of a cache key (default: True)
        type_name: Custom type name for debugging purposes

    Returns:
        Custom TypeDecorator class

    Raises:
        ValueError: If neither value_type nor deserialize+type_name are provided
    """
    if not value_type and not (deserialize and type_name):
        raise ValueError("Must specify either value_type or both deserialize and type_name")

    class CustomTypeDecorator(TypeDecorator):
        impl = sql_type
        cache_ok = cacheable

        if serialize:
            process_bind_param = serialize
        else:

            def process_bind_param(self, value: _PythonValueT, dialect: Dialect) -> _StorableValueT | None:
                return str(value) if value is not None else None

        if deserialize:
            process_result_value = deserialize
        else:

            def process_result_value(self, value: _StorableValueT, dialect: Dialect) -> _PythonValueT | None:
                return value_type(value) if value is not None else None  # type: ignore

    # Format type name for better debugging
    name = type_name or getattr(value_type, "__name__", "CustomType")
    CustomTypeDecorator.__name__ = f"{name}TypeDecorator"
    CustomTypeDecorator.__qualname__ = f"{name}TypeDecorator"

    return CustomTypeDecorator
