"""Declarative state with typed arguments and variables.

A :class:`State` subclass declares:

* :class:`Argument` fields — required values supplied at construction time.
* :class:`Variable` fields — optional values that default to ``None`` (or a
  supplied default) and can be supplied at construction time or assigned later.

Both kinds of fields support an optional ``validate`` callable that is
applied on every write.

Examples:
    >>> from yaddd import State, Argument, Variable

    >>> class OrderState(State):
    ...     user_id: int = Argument()
    ...     order_id: str = Argument(validate=str)
    ...     items: list[str] = Variable(default_factory=list)
    ...     total: float = Variable(default=0.0)

    Required arguments are checked at construction time:

    >>> state = OrderState(user_id=1, order_id="abc")
    >>> state.total
    0.0

    Variables can be supplied at construction time or enriched later, and are
    validated on every write:

    >>> state.total = "42.5"
    >>> state.total
    42.5
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, TypeVar, dataclass_transform

from yaddd.exceptions import ApplicationError


__all__ = ["Argument", "State", "StateError", "Variable"]


T = TypeVar("T")


def _identity(value: Any) -> Any:
    return value


@dataclass(frozen=True, slots=True)
class _ArgumentSpec:
    validate: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class _VariableSpec:
    validate: Callable[[Any], Any]
    default: Any
    default_factory: Callable[[], Any] | None


def Argument(validate: Callable[[Any], T] | None = None) -> Any:
    """Field specifier for a required state argument.

    Examples:
        >>> class OrderState(State):
        ...     user_id: int = Argument()
        ...     order_id: str = Argument(validate=str)

        Stories-style without annotations is also supported::

        >>> class OrderState(State):
        ...     user_id = Argument(int)
    """
    return _ArgumentSpec(validate=validate or _identity)


def Variable(
    validate: Callable[[Any], T] | None = None,
    *,
    default: T | None = None,
    default_factory: Callable[[], T] | None = None,
) -> Any:
    """Field specifier for a mutable state variable.

    Variables are optional at construction time. When no ``default`` or
    ``default_factory`` is supplied, the variable starts as ``None``.
    """
    if default is not None and default_factory is not None:
        raise ValueError("Specify either default or default_factory, not both")
    return _VariableSpec(
        validate=validate or _identity,
        default=default,
        default_factory=default_factory,
    )


class StateError(ApplicationError):
    """State was constructed or mutated outside of its declared schema."""


@dataclass(frozen=True, slots=True)
class _Field:
    name: str
    is_argument: bool
    validate: Callable[[Any], Any]
    default: Any
    default_factory: Callable[[], Any] | None


def _collect_fields(
    bases: tuple[type, ...],
    namespace: dict[str, Any],
) -> tuple[dict[str, _Field], set[str]]:
    base_fields: dict[str, _Field] = {}
    for base in reversed(bases):
        base_fields.update(getattr(base, "_fields", {}))

    current_fields: dict[str, _Field] = {}
    annotations = namespace.get("__annotations__", {})
    for attr_name, attr_value in list(namespace.items()):
        if isinstance(attr_value, (_ArgumentSpec, _VariableSpec)):
            current_fields[attr_name] = _build_field(
                attr_name, attr_value, annotations.get(attr_name)
            )
            del namespace[attr_name]

    fields = {**base_fields, **current_fields}
    new_field_names = set(current_fields.keys())
    return fields, new_field_names


def _build_field(
    name: str,
    specifier: _ArgumentSpec | _VariableSpec,
    annotation: Any,
) -> _Field:
    if isinstance(specifier, _ArgumentSpec):
        return _Field(
            name=name,
            is_argument=True,
            validate=specifier.validate,
            default=None,
            default_factory=None,
        )
    return _Field(
        name=name,
        is_argument=False,
        validate=specifier.validate,
        default=specifier.default,
        default_factory=specifier.default_factory,
    )


@dataclass_transform(field_specifiers=(Argument, Variable))
class StateType(type):
    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        fields, new_field_names = _collect_fields(bases, namespace)
        namespace["_fields"] = fields
        namespace["_arguments"] = {n: f for n, f in fields.items() if f.is_argument}
        namespace["_variables"] = {n: f for n, f in fields.items() if not f.is_argument}

        existing_slots: set[str] = set()
        for base in bases:
            existing_slots.update(getattr(base, "__slots__", ()))
        namespace["__slots__"] = tuple(new_field_names - existing_slots)

        return super().__new__(cls, name, bases, namespace, **kwargs)


class State(metaclass=StateType):
    """Base class for state objects with declared arguments and variables.

    Examples:
        >>> class PaymentState(State):
        ...     account_id: int = Argument()
        ...     amount: str = Argument(validate=str)
        ...     status: str = Variable(default="pending")
        ...     attempts: int = Variable(default=0)

        >>> payment = PaymentState(account_id=42, amount="100.00")
        >>> payment.status = "completed"
        >>> payment.attempts += 1

        Variables may also be supplied at construction time:

        >>> payment = PaymentState(
        ...     account_id=42,
        ...     amount="100.00",
        ...     status="completed",
        ... )
    """

    __slots__ = ()
    _fields: ClassVar[dict[str, _Field]]
    _arguments: ClassVar[dict[str, _Field]]
    _variables: ClassVar[dict[str, _Field]]

    def __init__(self, **arguments: Any) -> None:
        for name, value in arguments.items():
            if name not in self._fields:
                raise StateError(f"Unknown argument: {name!r}")
            field = self._fields[name]
            validated = field.validate(value)
            object.__setattr__(self, name, validated)

        missing = [name for name in self._arguments if name not in arguments]
        if missing:
            raise StateError(f"Missing required arguments: {', '.join(missing)!r}")

        for name, field in self._variables.items():
            if name in arguments:
                continue
            if field.default_factory is not None:
                value = field.default_factory()
            else:
                value = field.default
            object.__setattr__(self, name, value)

    def __setattr__(self, name: str, value: Any) -> None:
        if name not in self._fields:
            raise StateError(f"Unknown variable: {name!r}")
        field = self._fields[name]
        validated = field.validate(value)
        object.__setattr__(self, name, validated)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{name}={getattr(self, name)!r}" for name in self._fields)
        return f"{self.__class__.__name__}({attrs})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, State):
            return NotImplemented
        if self.__class__ is not other.__class__:
            return NotImplemented
        return all(getattr(self, name) == getattr(other, name) for name in self._fields)
