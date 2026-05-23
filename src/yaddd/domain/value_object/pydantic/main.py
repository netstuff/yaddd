"""Value objects, powered with pydantic v2."""

from types import UnionType
from typing import Annotated, Any, Type, TypeAlias, final, get_args, get_origin

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, SchemaSerializer, core_schema
from pydantic_core.core_schema import JsonSchema, SerializationInfo, SerializerFunctionWrapHandler
from typing_extensions import Self, assert_never

from ..base import ValidatedValue, ValueObject
from ..registry import VOBaseTypesRegistry


_PydanticType: TypeAlias = type[ValidatedValue] | Annotated  # type: ignore[valid-type]


def _validate_pydantic_type(
    _cls: Type, pydantic_type: _PydanticType
) -> None:  # ToDo good place to use specifications pattern https://github.com/pyDDD/yaddd/issues/3
    if get_origin(pydantic_type) is Annotated:  # Annotated support
        return _validate_pydantic_type(_cls, get_args(pydantic_type)[0])

    if isinstance(pydantic_type, UnionType):
        raise NotImplementedError(f"pydantic_type doesn't support unions: {_cls.__name__}")

    if not isinstance(get_origin(pydantic_type) or pydantic_type, type):
        raise TypeError(f"pydantic_type should be type: {_cls.__name__}")

    if not _pydantic_type_matches_with_parent(_cls, pydantic_type):
        raise TypeError(f"Types mismatch for {_cls.__name__}")


def _pydantic_type_matches_with_parent(_cls: Type, pydantic_type: _PydanticType) -> bool:
    """Ensure ValueObject type and pydantic_type match.

    Positive:
    class PositiveCaseVO(PydanticVO, IntValueObject):
        pydantic_type = int

    Negative:
    class NegativeCaseVO(PydanticVO, StringValueObject):
        pydantic_type = int
    """
    # Looking for latest ValueObject subclass in bases
    cls_based_on_value_object = next((base_cls for base_cls in _cls.__mro__ if issubclass(base_cls, ValueObject)), None)
    if cls_based_on_value_object is None:
        raise TypeError(f"PydanticVO's children should be based on ValueObject: {_cls.__name__}")

    # Looking for the latest registered in VOBaseTypesRegistry class
    ddd_vo_cls = next(
        (
            ddd_cls
            for ddd_cls in cls_based_on_value_object.__mro__
            if ddd_cls in VOBaseTypesRegistry.registered_vo_classes
        ),
        None,
    )

    return ddd_vo_cls is None or ddd_vo_cls in VOBaseTypesRegistry.select_matching_vo_classes(pydantic_type)


class PydanticVO:
    """Value Object with power of pydantic.

    The core idea is still the same as for ValueObject.
    Pydantic provides powerful and well-known tools for validation and this subclass of VO
        is created to use them!
    How methods are executed:
        1) During BaseModel initialization:
            a) if PydanticVO is not provided:
                - '__get_pydantic_core_schema__' targets method 'cast'
                - 'cast' method is called on provided value
                - 'cast' returns PydanticVO instance, that runs 'validate' on initialization
                - 'validate' executes chain of pydantic validators
                    and returns trusted value or raises ValidationError
                As result: PydanticVO instance is a value of BaseModel attribute,
                    that contains trusted data and shown in OpenAPI schema as  '_validated_value' attribute
            b) if PydanticVO is provided:
                All steps are the same, but 'cast' returns PydanticVO without initialization,
                because it is already initialized.

        2) Domain model requires VO instance, so we trust data, that VO contains
            (because of validation during initialization)
    """

    __pydantic_serializer__: SchemaSerializer
    pydantic_type: _PydanticType

    _pydantic_adapter: TypeAdapter[_PydanticType]
    _validated_value: ValidatedValue

    def __init_subclass__(cls, **kwargs):
        if not kwargs.pop("skip_pydantic_validation", False):
            if not (pydantic_type := getattr(cls, "pydantic_type", None)):
                raise TypeError(f"pydantic_type must be set for {cls.__name__}")
            _validate_pydantic_type(cls, pydantic_type)
            cls._pydantic_adapter = TypeAdapter(pydantic_type)

        super().__init_subclass__(**kwargs)

    @classmethod
    @final
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: GetCoreSchemaHandler) -> CoreSchema:
        """Validators to be called during initializing pydantic base model."""
        schema = core_schema.no_info_plain_validator_function(
            function=cls._cast,
            serialization=core_schema.wrap_serializer_function_ser_schema(
                cls._serialize, schema=cls._pydantic_adapter.core_schema, info_arg=True
            ),
        )
        # Followed by issue: https://github.com/pydantic/pydantic/issues/7779
        cls.__pydantic_serializer__ = SchemaSerializer(schema)
        return schema

    @classmethod
    @final
    def __get_pydantic_json_schema__(cls, _schema: JsonSchema, _handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        """VO representation in json schema."""
        json_schema: dict[str, Any] = cls._pydantic_adapter.json_schema()
        json_schema["title"] = cls.__name__
        return json_schema

    @classmethod
    @final
    def validate(cls, value: ValidatedValue | Any) -> ValidatedValue:
        """Validate value, using pydantic validators."""
        return cls._pydantic_adapter.validate_python(value)

    @classmethod
    @final
    def _cast(cls, value: ValidatedValue | Self) -> Self:
        """Cast VO type.

        We want either initialize VO and execute all validators or skip validation,
            if VO instance is provided.
        """
        if isinstance(value, cls):
            return value
        return cls(value)  # type: ignore[call-arg]

    def _serialize(self, handler: SerializerFunctionWrapHandler, info: SerializationInfo) -> Any:
        """Serialize value.

        Expected to be used within WrapSerializerFunction

        :param handler: partially serializes value by cls.pydantic_type logic
        :param info: serialization context
        """
        match info.mode:
            case "json":
                # use all annotated serializers instructions
                return handler(self._validated_value)

            case "python":
                # on application level we want to use VO
                return self

            case unexpected_mode:
                assert_never(unexpected_mode)
