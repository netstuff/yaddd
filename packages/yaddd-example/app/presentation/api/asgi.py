"""ASGI entrypoint of the API process.

Run it as ``api`` or ``uvicorn app.presentation.api.asgi:app``.
Both paths build the same container in the same process-local way, so probes,
logs and connection pools behave identically in development and in production.
"""

import uvicorn

from app.composition import build_container, get_settings
from app.presentation.api.app import create_app
from app.presentation.api.constants import UvicornTarget


__all__ = ["app", "main"]

app = create_app(build_container())


def main() -> None:
    """Serve the API with uvicorn."""
    settings = get_settings()
    uvicorn.run(
        UvicornTarget.API_APP,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
