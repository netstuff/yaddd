"""Infrastructure layer: adapters turning ports into concrete technologies.

Depends on ``domain`` and ``application``. This is the only layer allowed to
import SQLAlchemy, FastStream and pydantic-settings.
"""

__all__: list[str] = []
