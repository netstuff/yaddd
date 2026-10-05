"""Layer isolation rules for yaddd projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Layer:
    """A named architectural layer."""

    name: str

    def __str__(self) -> str:
        return self.name


DOMAIN = Layer("domain")
APPLICATION = Layer("application")
INFRASTRUCTURE = Layer("infrastructure")
PRESENTATION = Layer("presentation")
TESTING = Layer("testing")
UNKNOWN = Layer("unknown")

# Layer import rules: current_layer -> allowed imported layers.
# Stdlib and third-party imports are always allowed.
ALLOWED_IMPORTS: dict[Layer, set[Layer]] = {
    DOMAIN: {DOMAIN},
    APPLICATION: {DOMAIN, APPLICATION},
    INFRASTRUCTURE: {DOMAIN, APPLICATION, INFRASTRUCTURE},
    PRESENTATION: {DOMAIN, APPLICATION, PRESENTATION},
    TESTING: {DOMAIN, APPLICATION, INFRASTRUCTURE, PRESENTATION, TESTING},
    UNKNOWN: set(),
}


LAYER_BY_NAME: dict[str, Layer] = {
    "domain": DOMAIN,
    "application": APPLICATION,
    "infrastructure": INFRASTRUCTURE,
    "presentation": PRESENTATION,
}


def _directories_below_import_root(parts: list[str]) -> list[str]:
    """Return the directory segments that live under the project's import root.

    A ``src``-layout project imports from ``src``, so only the segments below
    the last ``src`` count. A flat layout (``app/domain/mod.py``) has no
    ``src`` segment, so every directory except the file itself is considered.
    """
    for idx in range(len(parts) - 1, -1, -1):
        if parts[idx] == "src":
            return parts[idx + 1 : -1]
    return parts[:-1]


def layer_from_path(path: Path) -> Layer:
    """Infer the architectural layer from a file path.

    A layer is the first directory named after a layer below the import root,
    so both layouts are recognised by shape, not by package name: flat
    (``app/domain/…``) and src (``<package>/src/<layer>/…``, …). Projects that
    do not happen to be called ``yaddd`` (``packages/yaddd-sqlalchemy/…``,
    ``apps/orders/src/application/…``) are checked too.
    """
    parts = list(path.parts)

    # Tests are allowed to import anything.
    if "tests" in parts or path.name.startswith("test_"):
        return TESTING

    # Plugin packages live in infrastructure by default.
    if "yaddd_sqlalchemy" in parts or "yaddd_pydantic" in parts:
        return INFRASTRUCTURE

    for directory in _directories_below_import_root(parts):
        layer = LAYER_BY_NAME.get(directory)
        if layer is not None:
            return layer

    return UNKNOWN


def layer_from_module(module_name: str) -> Layer:
    """Infer the architectural layer from a fully qualified module name.

    Any ``<package>.<layer>.…`` module is recognised, not only ``yaddd.…``, so
    applications built on yaddd (``app.domain.orders``, …) get the same layer
    isolation rules. A bare ``<layer>`` module (relative imports such as
    ``from .domain import …`` resolving to ``domain``) is recognised too.
    """
    if module_name.startswith("yaddd_sqlalchemy") or module_name.startswith("yaddd_pydantic"):
        return INFRASTRUCTURE

    parts = module_name.split(".")
    for candidate in parts[1:2] + parts[:1]:
        if candidate == "domain":
            return DOMAIN
        if candidate == "application":
            return APPLICATION
        if candidate == "infrastructure":
            return INFRASTRUCTURE
        if candidate == "presentation":
            return PRESENTATION
    return UNKNOWN


def package_root_from_path(path: Path) -> str | None:
    """Return the module root that owns ``path``.

    That is the directory directly above the layer directory — ``app`` for
    ``app/domain/mod.py``, ``yaddd`` for ``packages/yaddd/src/yaddd/domain/mod.py``
    — so first-party imports (``app.domain.…``) are told apart from third-party
    ones. Files below ``src`` but without a package directory
    (``src/domain/mod.py``) import as ``domain.…``: the layer directory itself
    is the module root. For files outside any layer directory the first
    directory below the import root is returned as a best-effort guess.
    """
    parts = list(path.parts)
    directories = _directories_below_import_root(parts)
    for idx, name in enumerate(directories):
        if name in LAYER_BY_NAME:
            if idx == 0:
                return name
            return directories[idx - 1]
    return directories[0] if directories else None
