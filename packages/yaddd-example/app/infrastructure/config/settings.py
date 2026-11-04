"""Environment-backed settings.

Every knob is a field with a development-friendly default, so the process
boots with no ``.env`` at all. Copy ``.env.example`` to ``.env`` to override
them; values are read from ``YADDD_*`` environment variables first.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.infrastructure.config.constants import AppEnv, ConfigDefaults, EnvFile, EnvPrefix
from app.shared.constants import Encoding


__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    """Configuration of every process in this application."""

    model_config = SettingsConfigDict(
        env_file=EnvFile.PATH,
        env_file_encoding=Encoding.UTF8,
        env_prefix=EnvPrefix.YADDD,
        extra="ignore",
    )

    app_name: str = ConfigDefaults.APP_NAME
    app_env: AppEnv = ConfigDefaults.APP_ENV
    log_level: str = ConfigDefaults.LOG_LEVEL

    api_host: str = ConfigDefaults.API_HOST
    api_port: int = ConfigDefaults.API_PORT
    api_workers: int = ConfigDefaults.API_WORKERS

    worker_host: str = ConfigDefaults.WORKER_HOST
    worker_port: int = ConfigDefaults.WORKER_PORT

    database_url: str = ConfigDefaults.DATABASE_URL
    db_echo: bool = ConfigDefaults.DB_ECHO

    broker_url: str = ConfigDefaults.BROKER_URL
    broker_events_channel: str = ConfigDefaults.BROKER_EVENTS_CHANNEL

    probe_timeout: float = Field(default=ConfigDefaults.PROBE_TIMEOUT, gt=0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, read from the environment once."""
    return Settings()
