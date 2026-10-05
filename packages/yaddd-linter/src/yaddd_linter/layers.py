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


def layer_from_path(path: Path) -> Layer:
    """Infer the architectural layer from a file path."""
    parts = list(path.parts)

    # Tests are allowed to import anything.
    if "tests" in parts or path.name.startswith("test_"):
        return TESTING

    # Main yaddd package layers. Search from the end to handle paths like
    # packages/yaddd/src/yaddd/domain/... correctly.
    for idx in range(len(parts) - 1, -1, -1):
        if parts[idx] != "yaddd":
            continue
        layer_idx = idx + 1
        if layer_idx < len(parts) and parts[layer_idx] == "src":
            layer_idx += 1
        if layer_idx < len(parts):
            layer_name = parts[layer_idx]
            if layer_name == "domain":
                return DOMAIN
            if layer_name == "application":
                return APPLICATION
            if layer_name == "infrastructure":
                return INFRASTRUCTURE
            if layer_name == "presentation":
                return PRESENTATION

    # Plugin packages live in infrastructure by default.
    if "yaddd_sqlalchemy" in parts or "yaddd_pydantic" in parts:
        return INFRASTRUCTURE

    return UNKNOWN


def layer_from_module(module_name: str) -> Layer:
    """Infer the architectural layer from a fully qualified module name."""
    if module_name.startswith("yaddd."):
        sub = module_name.split(".")[1]
        if sub == "domain":
            return DOMAIN
        if sub == "application":
            return APPLICATION
        if sub == "infrastructure":
            return INFRASTRUCTURE
        if sub == "presentation":
            return PRESENTATION
    if module_name.startswith("yaddd_sqlalchemy") or module_name.startswith("yaddd_pydantic"):
        return INFRASTRUCTURE
    return UNKNOWN
