import pytest

from src.yaddd.settings_config import (
    InvalidSettingError,
    MissingSettingError,
    Settings,
    SettingsError,
    UnsupportedSettingTypeError,
)


class ServerSettings(Settings):
    host: str = "localhost"
    port: int = 8000
    timeout: float = 0.5
    debug: bool = False
    api_key: str  # required: no default


class UnsupportedSettings(Settings):
    name: str = "app"
    tags: list[str] = []  # unsupported field type


def test_from_env_uses_class_defaults_when_variables_are_absent():
    settings = ServerSettings.from_env(environ={"API_KEY": "secret"})

    assert settings.host == "localhost"
    assert settings.port == 8000
    assert settings.timeout == 0.5
    assert settings.debug is False
    assert settings.api_key == "secret"


def test_from_env_reads_values_from_environ():
    settings = ServerSettings.from_env(
        environ={
            "HOST": "example.com",
            "PORT": "8080",
            "TIMEOUT": "1.5",
            "DEBUG": "true",
            "API_KEY": "secret",
        }
    )

    assert settings.host == "example.com"
    assert settings.port == 8080
    assert settings.timeout == 1.5
    assert settings.debug is True
    assert settings.api_key == "secret"


def test_from_env_reads_os_environ_by_default(monkeypatch):
    monkeypatch.setenv("YADDD_TEST_PORT", "7000")
    monkeypatch.setenv("YADDD_TEST_API_KEY", "secret")

    settings = ServerSettings.from_env(prefix="YADDD_TEST_")

    assert settings.port == 7000
    assert settings.api_key == "secret"


def test_from_env_applies_prefix_to_variable_names():
    settings = ServerSettings.from_env(environ={"APP_PORT": "9000", "APP_API_KEY": "secret"}, prefix="APP_")

    assert settings.port == 9000
    assert settings.api_key == "secret"
    assert settings.host == "localhost"


def test_from_env_raises_when_required_setting_is_missing():
    with pytest.raises(MissingSettingError, match="required setting 'API_KEY' is not set") as exc_info:
        ServerSettings.from_env(environ={})

    assert isinstance(exc_info.value, SettingsError)
    assert any("API_KEY environment variable" in note for note in exc_info.value.__notes__)


def test_from_env_rejects_invalid_int_value():
    with pytest.raises(InvalidSettingError, match="invalid value for setting 'PORT'") as exc_info:
        ServerSettings.from_env(environ={"API_KEY": "secret", "PORT": "not-a-number"})

    assert isinstance(exc_info.value, SettingsError)
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert any("int" in note for note in exc_info.value.__notes__)


def test_from_env_rejects_invalid_float_value():
    with pytest.raises(InvalidSettingError, match="invalid value for setting 'TIMEOUT'"):
        ServerSettings.from_env(environ={"API_KEY": "secret", "TIMEOUT": "soon"})


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", " yes ", "on"])
def test_from_env_parses_truthy_boolean_values(raw):
    settings = ServerSettings.from_env(environ={"API_KEY": "secret", "DEBUG": raw})

    assert settings.debug is True


@pytest.mark.parametrize("raw", ["0", "false", "No", "off"])
def test_from_env_parses_falsy_boolean_values(raw):
    settings = ServerSettings.from_env(environ={"API_KEY": "secret", "DEBUG": raw})

    assert settings.debug is False


def test_from_env_rejects_unrecognised_boolean_value():
    with pytest.raises(InvalidSettingError, match="invalid value for setting 'DEBUG'") as exc_info:
        ServerSettings.from_env(environ={"API_KEY": "secret", "DEBUG": "perhaps"})

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_from_env_keeps_empty_string_for_str_fields():
    settings = ServerSettings.from_env(environ={"HOST": "", "API_KEY": "secret"})

    assert settings.host == ""


def test_from_env_rejects_unsupported_field_type():
    with pytest.raises(UnsupportedSettingTypeError, match="unsupported type for setting 'tags'"):
        UnsupportedSettings.from_env(environ={})


def test_settings_instances_are_immutable():
    settings = ServerSettings.from_env(environ={"API_KEY": "secret"})

    with pytest.raises(AttributeError, match="immutable"):
        settings.port = 9000


def test_settings_cannot_be_constructed_directly():
    with pytest.raises(TypeError, match="from_env"):
        ServerSettings()
