"""Configuration loading from environment variables with typed access.

This module intentionally uses only the standard library so that the library
keeps zero mandatory dependencies. Settings are declared as classes with typed
class-level annotations; values are read from environment variables (or an
explicit mapping) and coerced to the declared types.

Example:

    from yaddd.settings_config import BaseSettings, Field

    class AppSettings(BaseSettings):
        env_prefix = "MYAPP_"

        debug: bool = Field(default=False)
        database_url: str = Field(env="DATABASE_URL")
        workers: int = Field(default=4)

    settings = AppSettings.load()
"""

import os
from collections.abc import Callable, Mapping
from typing import Any, ClassVar, Self, get_args, get_origin, get_type_hints


class SettingsError(Exception):
    """Base error for all settings-related problems."""


class MissingEnvVarError(SettingsError):
    """Raised when a required environment variable is not set."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Missing required environment variable: {name!r}")


class InvalidValueError(SettingsError):
    """Raised when an environment variable cannot be coerced to the declared type."""

    def __init__(self, name: str, raw: str, target_type: type):
        self.name = name
        self.raw = raw
        self.target_type = target_type
        super().__init__(
            f"Cannot convert environment variable {name!r} value {raw!r} "
            f"to {target_type.__name__}"
        )


_MISSING = object()
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})
_NONE_TYPE = type(None)


class _FieldInfo:
    """Internal description of a single settings field."""

    __slots__ = ("default", "env", "default_factory")

    def __init__(self, default: Any = _MISSING, env: str | None = None, default_factory: Callable[[], Any] | None = None):
        self.default = default
        self.env = env
        self.default_factory = default_factory

    @property
    def required(self) -> bool:
        return self.default is _MISSING and self.default_factory is None

    def get_default(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        return self.default


def Field(default: Any = _MISSING, *, env: str | None = None, default_factory: Callable[[], Any] | None = None) -> Any:
    """Declare a settings field with a default and/or an explicit env variable name.

    ``Field(...)`` with no arguments marks a required field.
    """
    return _FieldInfo(default, env=env, default_factory=default_factory)


def _strip_optional(annotation: Any) -> tuple[Any, bool]:
    """Return (inner_annotation, is_optional) for Optional[X] / X | None."""
    if get_origin(annotation) is None:
        return annotation, False
    args = tuple(arg for arg in get_args(annotation))
    if _NONE_TYPE in args:
        rest = tuple(arg for arg in args if arg is not _NONE_TYPE)
        inner = rest[0] if len(rest) == 1 else Any
        return inner, True
    return annotation, False


def _coerce_bool(name: str, raw: str) -> bool:
    lowered = raw.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise InvalidValueError(name, raw, bool)


def _coerce_value(name: str, raw: str, annotation: Any) -> Any:
    """Coerce a raw string to the declared annotation."""
    inner, _ = _strip_optional(annotation)
    origin = get_origin(inner)

    if inner is Any:
        return raw
    if origin in (list, tuple, set, frozenset):
        item_type = get_args(inner)[0] if get_args(inner) else str
        items = [_coerce_value(name, part.strip(), item_type) for part in raw.split(",") if part.strip()]
        return origin(items)
    if inner is bool:
        return _coerce_bool(name, raw)
    if inner is str:
        return raw
    try:
        return inner(raw)
    except (TypeError, ValueError) as exc:
        raise InvalidValueError(name, raw, inner) from exc


class SettingsMeta(type):
    """Collect declared fields and validate the settings class."""

    def __new__(mcls, name: str, bases: tuple, namespace: dict, **kwargs: Any):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)

        if name == "BaseSettings" and cls.__module__ == __name__:
            cls.__settings_fields__ = {}
            return cls

        annotations: dict[str, Any] = {}
        for base in reversed(cls.__mro__):
            annotations.update(getattr(base, "__annotations__", {}))

        # Start from the nearest parent's collected fields so defaults survive.
        fields: dict[str, _FieldInfo] = {}
        for base in cls.__mro__[1:]:
            parent_fields = base.__dict__.get("__settings_fields__")
            if parent_fields:
                fields.update(parent_fields)
                break

        for field_name, annotation in annotations.items():
            if field_name == "env_prefix":
                continue
            if get_origin(annotation) is ClassVar:
                continue
            default = namespace.get(field_name, _MISSING)
            if isinstance(default, _FieldInfo):
                fields[field_name] = default
            elif default is not _MISSING:
                fields[field_name] = _FieldInfo(default=default)
            else:
                fields.setdefault(field_name, _FieldInfo())

        # Resolve forward references / string annotations against the class namespace.
        try:
            resolved = get_type_hints(cls)
        except Exception:
            resolved = annotations
        cls.__settings_types__ = {f: resolved.get(f, annotations.get(f, Any)) for f in fields}
        cls.__settings_fields__ = fields

        # Field declarations must not shadow instance values: __getattr__ is only
        # consulted when normal attribute lookup fails, so remove the class attrs.
        for field_name in fields:
            if field_name in getattr(cls, "__dict__", {}):
                delattr(cls, field_name)
        return cls


class BaseSettings(metaclass=SettingsMeta):
    """Base class for typed environment-variable-backed settings.

    Subclasses declare fields as typed class attributes, optionally wrapped in
    :func:`Field`. Use :meth:`load` to build an instance from ``os.environ`` (or
    a provided mapping).
    """

    env_prefix: ClassVar[str] = ""

    __settings_fields__: ClassVar[dict[str, _FieldInfo]]
    __settings_types__: ClassVar[dict[str, Any]]

    @classmethod
    def load(cls, env: Mapping[str, str] | None = None) -> Self:
        """Build a settings instance from ``env`` (defaults to ``os.environ``)."""
        source = os.environ if env is None else env
        values: dict[str, Any] = {}
        for name, info in cls.__settings_fields__.items():
            annotation = cls.__settings_types__[name]
            _, is_optional = _strip_optional(annotation)
            env_name = info.env or f"{cls.env_prefix}{name.upper()}"

            raw = source.get(env_name)
            if raw is None or (is_optional and raw.strip() == ""):
                if info.required and not is_optional:
                    raise MissingEnvVarError(env_name)
                values[name] = info.get_default()
                continue

            inner, _ = _strip_optional(annotation)
            if raw.strip() == "" and not _is_sequence(inner):
                if info.required:
                    raise InvalidValueError(env_name, raw, inner if inner is not Any else str)
                values[name] = info.get_default()
                continue

            values[name] = _coerce_value(env_name, raw, annotation)

        instance = cls.__new__(cls)
        object.__setattr__(instance, "_values", values)
        return instance

    def __getattr__(self, name: str) -> Any:
        try:
            values = object.__getattribute__(self, "_values")
        except AttributeError:
            raise AttributeError(name) from None
        if name in values:
            return values[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable; use {type(self).__name__}.load() to build a new instance")

    def __getitem__(self, name: str) -> Any:
        return self._values[name]

    def __contains__(self, name: object) -> bool:
        return name in self._values

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and self._values == other._values  # noqa: E721

    def __repr__(self) -> str:
        body = ", ".join(f"{k}={v!r}" for k, v in self._values.items())
        return f"{type(self).__name__}({body})"

    def as_dict(self) -> dict[str, Any]:
        """Return a shallow copy of the resolved values."""
        return dict(self._values)


def _is_sequence(annotation: Any) -> bool:
    inner, _ = _strip_optional(annotation)
    return get_origin(inner) in (list, tuple, set, frozenset)
