"""Process configuration defaults."""

from enum import StrEnum


__all__ = ["AppEnv", "ConfigDefaults", "EnvFile", "EnvPrefix", "ProcessSuffix"]


class AppEnv(StrEnum):
    """Known deployment environments."""

    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigDefaults:
    """Default values for :class:`~app.infrastructure.config.settings.Settings`."""

    APP_NAME = "yaddd-template"
    APP_ENV = AppEnv.LOCAL
    LOG_LEVEL = "INFO"
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    API_WORKERS = 1
    WORKER_HOST = "0.0.0.0"
    WORKER_PORT = 8001
    DATABASE_URL = "sqlite+aiosqlite:///./yaddd-template.db"
    DB_ECHO = False
    BROKER_URL = "redis://localhost:6379/0"
    BROKER_EVENTS_CHANNEL = "domain-events"
    PROBE_TIMEOUT = 2.0


class EnvPrefix:
    """Prefix of every environment variable read by settings."""

    YADDD = "YADDD_"


class EnvFile:
    """Dotenv configuration."""

    PATH = ".env"


class ProcessSuffix:
    """Suffixes appended to process names."""

    API = ".api"
