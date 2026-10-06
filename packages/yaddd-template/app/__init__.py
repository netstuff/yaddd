"""yaddd-template — application skeleton built on the yaddd building blocks.

The package is layered: ``domain`` holds the business model, ``application``
orchestrates use cases, ``infrastructure`` adapts ports to concrete
technologies and ``presentation`` exposes entrypoints. ``composition`` is the
only place allowed to import every layer at once.
"""

__all__: list[str] = []
