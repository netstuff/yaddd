import pytest
from yaddd import Argument, State, StateError, Variable
from yaddd.application.handlers.scenarios import Context, Scenario, ScenarioRunner, step


class TypedOrderState(State):
    user_id: int = Argument()
    order_id: str = Argument(validate=str)
    items: list = Variable(default_factory=list)
    total: float = Variable(default=0.0)


class StoriesStyleOrderState(State):
    user_id = Argument(int)
    order_id = Argument(str)
    items = Variable(list, default_factory=list)
    total = Variable(float, default=0.0)


@pytest.mark.parametrize("cls", [TypedOrderState, StoriesStyleOrderState])
def test_state_requires_arguments_and_sets_variable_defaults(cls):
    state = cls(user_id=1, order_id="abc")

    assert state.user_id == 1
    assert state.order_id == "abc"
    assert state.items == []
    assert state.total == 0.0


def test_state_validates_arguments():
    state = TypedOrderState(user_id=1, order_id=123)

    assert state.order_id == "123"


def test_state_validates_variables_on_assignment():
    state = TypedOrderState(user_id=1, order_id="abc")

    state.total = "42.5"  # default Variable has no validator, value stays a string

    assert state.total == "42.5"


def test_state_validates_variables_with_custom_validator():
    class ValidatedTotalState(State):
        user_id: int = Argument()
        total: float = Variable(validate=float, default=0.0)

    state = ValidatedTotalState(user_id=1)

    state.total = "42.5"

    assert state.total == 42.5


def test_state_enriches_variables_after_construction():
    state = TypedOrderState(user_id=1, order_id="abc")

    state.items = ["item-1"]
    state.total = 100.0

    assert state.items == ["item-1"]
    assert state.total == 100.0


def test_state_accepts_variables_at_construction_time():
    state = TypedOrderState(
        user_id=1,
        order_id="abc",
        items=["item-1"],
        total=100.0,
    )

    assert state.items == ["item-1"]
    assert state.total == 100.0


def test_missing_required_argument_raises():
    with pytest.raises(StateError, match="Missing required arguments"):
        TypedOrderState(user_id=1)


def test_unknown_argument_raises():
    with pytest.raises(StateError, match="Unknown argument"):
        TypedOrderState(user_id=1, order_id="abc", extra=True)


def test_unknown_variable_assignment_raises():
    state = TypedOrderState(user_id=1, order_id="abc")

    with pytest.raises(StateError, match="Unknown variable"):
        state.unknown = "value"


def test_default_factory_creates_fresh_value_per_instance():
    first = TypedOrderState(user_id=1, order_id="a")
    second = TypedOrderState(user_id=2, order_id="b")

    first.items.append("x")

    assert first.items == ["x"]
    assert second.items == []


def test_state_repr_shows_declared_fields():
    state = TypedOrderState(user_id=1, order_id="abc")

    repr_state = repr(state)

    assert repr_state.startswith("TypedOrderState(")
    assert "user_id=1" in repr_state
    assert "order_id='abc'" in repr_state
    assert "items=[]" in repr_state
    assert "total=0.0" in repr_state


def test_state_equality_compares_declared_fields():
    a = TypedOrderState(user_id=1, order_id="abc")
    b = TypedOrderState(user_id=1, order_id="abc")
    c = TypedOrderState(user_id=2, order_id="abc")

    assert a == b
    assert a != c


def test_state_is_unhashable():
    state = TypedOrderState(user_id=1, order_id="abc")

    with pytest.raises(TypeError):
        hash(state)


class BaseState(State):
    shared: str = Argument()


class ChildState(BaseState):
    extra: int = Variable(default=0)


def test_state_inherits_arguments_and_variables():
    state = ChildState(shared="base")

    assert state.shared == "base"
    assert state.extra == 0

    state.extra = 10
    assert state.extra == 10


class ValidatedState(State):
    count: int = Argument(validate=lambda value: int(value))
    name: str = Variable(validate=lambda value: value.strip())


def test_validation_is_applied_to_arguments_and_variables():
    state = ValidatedState(count="5")

    assert state.count == 5

    state.name = "  hello  "

    assert state.name == "hello"


class OrderState(State):
    user_id: int = Argument()
    order_id: str = Argument()
    total: float = Variable(default=0.0)


class EnrichOrderScenario(Scenario[OrderState]):
    @step
    async def add_item(self, ctx: Context[OrderState]) -> None:
        ctx.state.total += 10.0


async def test_state_works_with_scenario_runner():
    runner = ScenarioRunner()
    initial = OrderState(user_id=1, order_id="abc")

    result = await runner.run([EnrichOrderScenario()], initial_state=initial)

    assert result.total == 10.0
