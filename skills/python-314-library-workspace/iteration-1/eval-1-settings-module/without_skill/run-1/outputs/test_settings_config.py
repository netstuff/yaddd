"""Tests for yaddd.settings_config (stdlib-only settings loader)."""

import pytest

from yaddd.settings_config import (
    BaseSettings,
    Field,
    InvalidValueError,
    MissingEnvVarError,
)


class SimpleSettings(BaseSettings):
    debug: bool = Field(default=False)
    workers: int = Field(default=4)
    name: str = Field(default="unnamed")


class RequiredSettings(BaseSettings):
    database_url: str = Field(env="DATABASE_URL")
    api_key: str  # required, env name derived from the field name


class PrefixedSettings(BaseSettings):
    env_prefix = "MYAPP_"

    port: int = Field(default=8000)
    timeout: float = Field(default=1.5)


class TypedSettings(BaseSettings):
    retries: int = Field(default=3)
    ratio: float = Field(default=0.5)
    enabled: bool = Field(default=False)
    tags: list[str] = Field(default_factory=list)
    plain_default: str = "from-class"  # declared without Field()


class OptionalSettings(BaseSettings):
    maybe_number: int | None = None
    maybe_flag: bool | None = None


def test_defaults_applied_when_env_missing():
    settings = SimpleSettings.load(env={})
    assert settings.debug is False
    assert settings.workers == 4
    assert settings.name == "unnamed"


def test_env_overrides_defaults():
    settings = SimpleSettings.load(env={"DEBUG": "true", "WORKERS": "8", "NAME": "svc"})
    assert settings.debug is True
    assert settings.workers == 8
    assert settings.name == "svc"


def test_bool_accepts_common_forms():
    for raw in ("1", "true", "TRUE", "yes", "on"):
        assert SimpleSettings.load(env={"DEBUG": raw}).debug is True
    for raw in ("0", "false", "no", "off"):
        assert SimpleSettings.load(env={"DEBUG": raw}).debug is False
    with pytest.raises(InvalidValueError):
        SimpleSettings.load(env={"DEBUG": "maybe"})


def test_int_and_float_coercion():
    settings = TypedSettings.load(env={"RETRIES": "10", "RATIO": "2.25"})
    assert settings.retries == 10
    assert isinstance(settings.retries, int)
    assert settings.ratio == 2.25
    assert isinstance(settings.ratio, float)


def test_invalid_int_raises():
    with pytest.raises(InvalidValueError):
        TypedSettings.load(env={"RETRIES": "ten"})


def test_list_parsing_from_comma_separated():
    settings = TypedSettings.load(env={"TAGS": "a, b ,c"})
    assert settings.tags == ["a", "b", "c"]


def test_list_factory_default():
    settings = TypedSettings.load(env={})
    assert settings.tags == []
    settings.tags.append("x")  # fresh object per instance; mutation is safe
    assert TypedSettings.load(env={}).tags == []


def test_plain_class_attribute_default():
    settings = TypedSettings.load(env={})
    assert settings.plain_default == "from-class"
    assert TypedSettings.load(env={"PLAIN_DEFAULT": "from-env"}).plain_default == "from-env"


def test_required_field_missing_raises():
    with pytest.raises(MissingEnvVarError) as exc_info:
        RequiredSettings.load(env={})
    assert exc_info.value.name == "DATABASE_URL"


def test_required_field_from_explicit_env_name():
    settings = RequiredSettings.load(env={"DATABASE_URL": "postgres://x", "API_KEY": "secret"})
    assert settings.database_url == "postgres://x"
    assert settings.api_key == "secret"


def test_env_prefix_is_applied():
    settings = PrefixedSettings.load(env={"MYAPP_PORT": "9000", "MYAPP_TIMEOUT": "3.5"})
    assert settings.port == 9000
    assert settings.timeout == 3.5
    # Without the prefix the variable is ignored.
    assert PrefixedSettings.load(env={"PORT": "9000"}).port == 8000


def test_optional_fields():
    settings = OptionalSettings.load(env={})
    assert settings.maybe_number is None
    assert settings.maybe_flag is None

    settings = OptionalSettings.load(env={"MAYBE_NUMBER": "42", "MAYBE_FLAG": "yes"})
    assert settings.maybe_number == 42
    assert settings.maybe_flag is True

    # Empty env value for an optional field falls back to None.
    assert OptionalSettings.load(env={"MAYBE_NUMBER": ""}).maybe_number is None


def test_instances_are_immutable():
    settings = SimpleSettings.load(env={})
    with pytest.raises(AttributeError):
        settings.workers = 99


def test_mapping_access_and_containment():
    settings = SimpleSettings.load(env={"WORKERS": "2"})
    assert settings["workers"] == 2
    assert "workers" in settings
    assert "nope" not in settings
    with pytest.raises(KeyError):
        settings["nope"]


def test_as_dict_repr_and_equality():
    env = {"DEBUG": "true", "WORKERS": "2", "NAME": "svc"}
    first = SimpleSettings.load(env=env)
    second = SimpleSettings.load(env=env)
    assert first == second
    assert first.as_dict() == {"debug": True, "workers": 2, "name": "svc"}
    assert "SimpleSettings(" in repr(first)
    assert first != SimpleSettings.load(env={})


def test_subclass_inherits_parent_fields():
    class ExtendedSettings(SimpleSettings):
        extra: str = Field(default="x")

    settings = ExtendedSettings.load(env={"WORKERS": "7", "EXTRA": "y"})
    assert settings.workers == 7
    assert settings.extra == "y"
    assert settings.debug is False
