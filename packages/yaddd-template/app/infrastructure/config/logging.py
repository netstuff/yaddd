"""Process logging setup.

Entry points call :func:`configure_logging` once, at startup, before any
request is served: libraries must not configure logging on import.
"""

import logging

from app.infrastructure.config.settings import Settings


__all__ = ["configure_logging"]

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(settings: Settings) -> None:
    """Configure root logging for a process, replacing any previous setup."""
    logging.basicConfig(level=settings.log_level.upper(), format=LOG_FORMAT, force=True)
