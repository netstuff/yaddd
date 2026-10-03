"""Public API of the yaddd package.

This is the file that would live at src/yaddd/__init__.py. It re-exports the
public surface of the settings module so users can write:

    from yaddd import BaseSettings, Field

instead of importing from the submodule directly.
"""

from yaddd.settings_config import (
    BaseSettings,
    Field,
    InvalidValueError,
    MissingEnvVarError,
    SettingsError,
)

__all__ = [
    "BaseSettings",
    "Field",
    "InvalidValueError",
    "MissingEnvVarError",
    "SettingsError",
]
