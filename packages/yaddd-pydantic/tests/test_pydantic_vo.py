import json
from collections.abc import Callable
from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from yaddd.domain import SensitiveValueObject, ValueObject
from yaddd.testing import VoSerializationContract
from yaddd_pydantic import PydanticVO


class PositiveTotal(PydanticVO[int]):
    pydantic_type = Annotated[int, Field(gt=0)]


class Secret(SensitiveValueObject[str], PydanticVO[str]):
    pydantic_type = Annotated[str, Field(min_length=8)]


class OrderModel(BaseModel):
    total: PositiveTotal


class Credentials(BaseModel):
    password: Secret


def test_raw_input_becomes_vo_instance():
    model = OrderModel(total=5)

    assert isinstance(model.total, PositiveTotal)
    assert model.total.value == 5


def test_vo_instance_input_is_preserved():
    total = PositiveTotal(10)

    assert OrderModel(total=total).total is total


def test_pydantic_constraint_violation_raises():
    with pytest.raises(ValidationError):
        OrderModel(total=-1)


def test_vo_construction_outside_model_uses_pydantic_validation():
    with pytest.raises(ValidationError):
        PositiveTotal(0)


def test_model_dump_contains_primitive():
    dumped = OrderModel(total=5).model_dump()

    assert dumped["total"] == 5
    assert not isinstance(dumped["total"], ValueObject)


def test_model_dump_json_contains_primitive():
    assert json.loads(OrderModel(total=5).model_dump_json())["total"] == 5


def test_json_schema_shows_primitive_shape():
    schema = OrderModel.model_json_schema()

    assert schema["properties"]["total"]["type"] == "integer"
    assert schema["properties"]["total"]["exclusiveMinimum"] == 0


def test_sensitive_vo_repr_is_masked():
    model = Credentials(password="super-secret-1")

    assert "super-secret-1" not in repr(model)
    assert "MASKED" in repr(model)


def test_sensitive_vo_explicit_dump_contains_raw_value():
    assert Credentials(password="super-secret-1").model_dump()["password"] == "super-secret-1"


def test_sensitive_vo_constraint_violation_raises():
    with pytest.raises(ValidationError):
        Credentials(password="short")


class TestPydanticVoSerialization(VoSerializationContract):
    """The contract suite proves serialization conformance via pydantic hooks."""

    @pytest.fixture
    def vo(self) -> ValueObject[Any]:
        return PositiveTotal(5)

    @pytest.fixture
    def invalid_raw(self) -> Any:
        return -1

    @pytest.fixture
    def dump(self) -> Callable[[ValueObject[Any]], Any]:
        adapter: TypeAdapter[PositiveTotal] = TypeAdapter(PositiveTotal)
        return adapter.dump_python

    @pytest.fixture
    def load(self) -> Callable[[Any], ValueObject[Any]]:
        adapter: TypeAdapter[PositiveTotal] = TypeAdapter(PositiveTotal)
        return adapter.validate_python

    @pytest.fixture
    def sensitive_vo(self) -> ValueObject[Any]:
        return Secret("super-secret-1")

    @pytest.fixture
    def container_repr(self) -> Callable[[ValueObject[Any]], str]:
        def make_repr(vo: ValueObject[Any]) -> str:
            return repr(Credentials(password=vo))

        return make_repr
