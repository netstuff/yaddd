"""Pydantic v2 value objects: VOs as first-class field types in pydantic models."""

from typing import Any, ClassVar, Self, cast

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema
from yaddd.domain.value_object import ValueObject


__all__ = ["PydanticVO"]


class PydanticVO[V](ValueObject[V]):
    """``ValueObject`` validated and serialized by pydantic v2.

    Subclass and declare ``pydantic_type`` — the type pydantic uses for
    validation and JSON Schema::

        class PositiveTotal(PydanticVO[int]):
            pydantic_type = Annotated[int, Field(gt=0)]

    Behavior:

    - ``validate`` runs the ``TypeAdapter(pydantic_type)`` chain, so pydantic
      constraints double as VO validation — even outside any model;
    - a VO field in a ``BaseModel`` accepts both a raw value (validated into
      a VO instance) and an existing VO instance (kept as is);
    - serialization produces the primitive: ``model_dump()`` and
      ``model_dump_json()`` contain ``vo.value``, never a VO repr;
    - JSON Schema (OpenAPI) shows the ``pydantic_type`` shape.

    Combine with ``SensitiveValueObject`` to keep masking::

        class Password(SensitiveValueObject[str], PydanticVO[str]):
            pydantic_type = Annotated[str, Field(min_length=8)]

    Masking is preserved: the model's ``repr`` uses the VO's masked
    ``__repr__`` and ``str`` still raises ``SensitiveValueAccessError``.
    A pydantic dump is an explicit serialization act, so ``model_dump()`` /
    ``model_dump_json()`` contain the raw value — treat dumped output as
    sensitive and keep it out of logs.
    """

    pydantic_type: ClassVar[Any]

    _adapter_instance: ClassVar[TypeAdapter[Any] | None] = None

    @classmethod
    def validate(cls, value: V) -> V:
        """Validate the raw value through the ``pydantic_type`` chain."""
        return cast("V", cls._type_adapter().validate_python(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        """Accept raw values and VO instances; serialize to the primitive."""
        return core_schema.no_info_plain_validator_function(
            cls._accept,
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize,
                return_schema=cls._type_adapter().core_schema,
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        """JSON Schema comes from ``pydantic_type``: the primitive shape."""
        json_schema = cls._type_adapter().json_schema()
        json_schema["title"] = cls.__name__
        return json_schema

    @classmethod
    def _type_adapter(cls) -> TypeAdapter[Any]:
        """Lazily built and cached per concrete VO class."""
        adapter = cls.__dict__.get("_adapter_instance")
        if adapter is None:
            adapter = TypeAdapter(cls.pydantic_type)
            cls._adapter_instance = adapter
        return cast("TypeAdapter[Any]", adapter)

    @classmethod
    def _accept(cls, value: Any) -> Self:
        """Pass VO instances through; validate raw values into VOs."""
        if isinstance(value, cls):
            return value
        return cls(value)


def _serialize(vo: ValueObject[Any]) -> Any:
    return vo.value
