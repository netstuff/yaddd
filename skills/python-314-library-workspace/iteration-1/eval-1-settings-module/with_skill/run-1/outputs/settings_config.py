"""Environment-backed settings with typed access, stdlib-only.

Users declare a settings class by subclassing :class:`Settings`: each
annotated class attribute is a setting, and the attribute value is its
default. A field declared without a default is required and must be provided
through an environment variable. Instances are built with
:meth:`Settings.from_env` and are immutable.
"""

import os
from collections.abc import Callable, Mapping
from typing import Any, ClassVar, Final, Self, get_origin, get_type_hints


__all__ = [
    "Settings",
    "SettingsError",
    "MissingSettingError",
    "InvalidSettingError",
    "UnsupportedSettingTypeError",
]


class SettingsError(Exception):
    """Base class for all settings errors."""


class MissingSettingError(SettingsError):
    """A required setting has no default and its environment variable is not set."""


class InvalidSettingError(SettingsError):
    """An environment variable value cannot be converted to the declared type."""


class UnsupportedSettingTypeError(SettingsError):
    """A setting is declared with a type the loader cannot convert from a string."""


class Settings:
    """Base class for environment-backed settings.

    Supported field types: ``str``, ``int``, ``float``, ``bool``.

    Instances are immutable value objects; they cannot be constructed
    directly — use :meth:`from_env`.
    """

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(f"{type(self).__name__} cannot be constructed directly; use {type(self).__name__}.from_env()")

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable; attribute {name!r} cannot be assigned")

    @classmethod
    def from_env(cls, *, environ: Mapping[str, str] | None = None, prefix: str = "") -> Self:
        """Load settings from environment variables.

        Field ``name`` is read from the variable ``prefix + name.upper()``.
        When the variable is absent, the class-level default is used; a field
        without a default is required and raises :class:`MissingSettingError`.

        :param environ: source mapping, defaults to ``os.environ``. Passing an
            explicit mapping keeps call sites (and tests) hermetic.
        :param prefix: prefix prepended to every variable name, e.g.
            ``"MYAPP_"`` reads ``MYAPP_PORT`` for a ``port`` field.
        """
        source = os.environ if environ is None else environ
        fields = {name: tp for name, tp in get_type_hints(cls).items() if get_origin(tp) is not ClassVar}
        for name, tp in fields.items():
            if tp not in _PARSERS:
                error = UnsupportedSettingTypeError(f"unsupported type for setting {name!r}: {tp!r}")
                error.add_note(f"supported types: {', '.join(parser.__name__ for parser in _PARSERS)}")
                raise error

        instance = cls.__new__(cls)
        for name, tp in fields.items():
            env_name = f"{prefix}{name.upper()}"
            default = getattr(cls, name, _MISSING)
            raw = source.get(env_name)
            if raw is None:
                if default is _MISSING:
                    missing = MissingSettingError(f"required setting {env_name!r} is not set")
                    missing.add_note(f"set the {env_name} environment variable or give {name!r} a default")
                    raise missing
                value: object = default
            else:
                value = _convert(name=name, env_name=env_name, raw=raw, tp=tp)
            object.__setattr__(instance, name, value)
        return instance


_MISSING: Final = object()

_TRUE_VALUES: Final = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES: Final = frozenset({"0", "false", "no", "off"})


def _parse_bool(raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"not a boolean: {raw!r}")


_PARSERS: Final[dict[type[object], Callable[[str], object]]] = {
    str: lambda raw: raw,
    int: int,
    float: float,
    bool: _parse_bool,
}


def _convert(*, name: str, env_name: str, raw: str, tp: Any) -> object:
    parser = _PARSERS[tp]
    try:
        return parser(raw)
    except ValueError as exc:
        error = InvalidSettingError(f"invalid value for setting {env_name!r}")
        error.add_note(f"expected a value of type {tp.__name__} for field {name!r}")
        raise error from exc
