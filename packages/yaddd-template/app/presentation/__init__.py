"""Presentation layer: entrypoints (HTTP API, broker worker, CLI).

Depends on ``domain`` and ``application`` only — every concrete adapter is
injected from the composition root, which keeps frameworks replaceable and the
layer testable without a running server.
"""

__all__: list[str] = []
