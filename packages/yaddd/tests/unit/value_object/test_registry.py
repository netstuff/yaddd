import datetime
from abc import ABC
from typing import Generic, TypeVar

import pytest

from yaddd.domain.value_object import (
    DatetimeValueObject,
    DateValueObject,
    DictValueObject,
    ValueObject,
    VOBaseTypesRegistry,
)


def _unregister_class(cls: type, registry: VOBaseTypesRegistry = VOBaseTypesRegistry) -> None:
    """Helper to clean up registry after test."""
    del registry._cls_to_basic_types[cls]
    for basic_type in registry._extract_basic_types(cls):
        del registry._basic_type_to_cls[basic_type]


def test_registration_of_value_object_subclass():
    class TestVO(ValueObject[bool]):
        pass

    VOBaseTypesRegistry.register(TestVO)

    assert TestVO in VOBaseTypesRegistry.registered_vo_classes
    assert bool in VOBaseTypesRegistry._basic_type_to_cls

    _unregister_class(TestVO)


def test_registration_of_non_value_object_fails():
    with pytest.raises(TypeError, match="must be a ValueObject subclass"):
        VOBaseTypesRegistry.register(int)


def test_registration_with_union_type_parameter():
    class SuperInt(int):
        pass

    class SuperStr(str):
        pass

    class UnionVO(ValueObject[SuperStr | SuperInt]):
        pass

    VOBaseTypesRegistry.register(UnionVO)

    assert UnionVO in VOBaseTypesRegistry.registered_vo_classes
    assert SuperInt in VOBaseTypesRegistry._basic_type_to_cls
    assert SuperStr in VOBaseTypesRegistry._basic_type_to_cls

    _unregister_class(UnionVO)


def test_date_type_matching():
    result = VOBaseTypesRegistry.select_most_matching_vo_class(datetime.date)
    assert result == DateValueObject


def test_datetime_type_matching():
    result = VOBaseTypesRegistry.select_most_matching_vo_class(datetime.datetime)
    assert result == DatetimeValueObject


def test_complex_inheritance_cases():
    class BaseVO(ValueObject[complex], ABC):
        pass

    class Mixin:
        pass

    class VOWithMixin(Mixin, ValueObject[complex], ABC):
        pass

    class ExtendedVO(ValueObject[complex]):
        def extra_method(self):
            pass

    class GenericMixin(Generic[TypeVar("T")]):
        pass

    class VOWithGenericMixin(ExtendedVO, GenericMixin[str], ValueObject[complex], Mixin):
        pass

    test_cases = [BaseVO, VOWithMixin, ExtendedVO, VOWithGenericMixin]

    for vo_class in test_cases:
        VOBaseTypesRegistry.register(vo_class)
        assert vo_class in VOBaseTypesRegistry.registered_vo_classes
        assert complex in VOBaseTypesRegistry._basic_type_to_cls
        _unregister_class(vo_class)


def test_multiple_generic_bases_error():
    class ChildVO(ValueObject[TypeVar("T")]):
        pass

    class InvalidVO(ChildVO[str], ValueObject[complex]):
        pass

    with pytest.raises(TypeError, match="Multiple generic bases"):
        VOBaseTypesRegistry.register(InvalidVO)


@pytest.mark.parametrize(
    "dict_type",
    [
        dict,
        dict[str, str],
    ],
)
def test_dict_type_matching(dict_type):
    result = VOBaseTypesRegistry.select_most_matching_vo_class(dict_type)
    assert result == DictValueObject
