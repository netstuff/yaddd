"""Configuration discovery for yaddd-linter."""

from __future__ import annotations

import json
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from yaddd_linter.rules import ALL_CODES


@dataclass(frozen=True, slots=True)
class LayerPolicy:
    """Import policy for one architectural layer."""

    imports: frozenset[str] = frozenset()
    third_party: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class Config:
    """Resolved linter configuration."""

    select: frozenset[str]
    ignore: frozenset[str]
    exclude: tuple[str, ...]
    layers: Mapping[str, LayerPolicy] = field(default_factory=dict[str, LayerPolicy])

    def is_enabled(self, code: str) -> bool:
        """Return True if the violation code should be reported."""
        if self.select and code not in self.select:
            return False
        return code not in self.ignore

    def policy_for(self, layer: str) -> LayerPolicy | None:
        """Return the configured policy for a layer, if any."""
        return self.layers.get(layer)


def _tool_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract the ``[tool.yaddd-linter]`` table if present."""
    return raw.get("tool", {}).get("yaddd-linter", {}) or {}


def _as_str_set(value: Any) -> frozenset[str]:
    """Coerce a string or sequence of strings into a set."""
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset({value})
    if isinstance(value, list | tuple | set | frozenset):
        return frozenset(str(item) for item in cast(Iterable[Any], value) if isinstance(item, str))
    return frozenset()


def _normalize_codes(codes: frozenset[str]) -> frozenset[str]:
    """Validate and normalize rule codes."""
    unknown = codes - ALL_CODES
    if unknown:
        raise ValueError(f"Unknown yaddd-linter rule codes: {sorted(unknown)}")
    return codes


def load_config(path: Path | None = None, layers_path: Path | None = None) -> Config:
    """Load configuration from ``pyproject.toml``.

    If ``path`` is given, it is used directly; otherwise the nearest
    ``pyproject.toml`` is discovered by walking up from the current working
    directory.  Missing or invalid configuration falls back to defaults.
    Layer policy is read from ``.yaddd/layers.json`` next to ``pyproject.toml``
    unless ``layers_path`` is given explicitly.
    """
    if path is None:
        path = _find_pyproject(Path.cwd())

    return _load_config_at(path, layers_path)


def load_config_for_path(file_path: Path) -> Config:
    """Load configuration from the nearest ``pyproject.toml`` to ``file_path``."""
    return _load_config_at(_find_pyproject(file_path))


def _load_config_at(path: Path | None, layers_path: Path | None = None) -> Config:
    """Parse the linter section from the given ``pyproject.toml`` path."""
    raw: dict[str, Any] = {}
    if path is not None:
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            raw = {}

    tool = _tool_config(raw)
    select = _normalize_codes(_as_str_set(tool.get("select")))
    ignore = _normalize_codes(_as_str_set(tool.get("ignore")))
    exclude = tuple(str(item) for item in tool.get("exclude", []) if isinstance(item, str))
    layers = _load_layers(layers_path, path)
    return Config(select=select, ignore=ignore, exclude=exclude, layers=layers)


def _load_layers(layers_path: Path | None, pyproject_path: Path | None) -> dict[str, LayerPolicy]:
    """Load ``.yaddd/layers.json`` when present."""
    candidate = layers_path
    if candidate is None and pyproject_path is not None:
        candidate = pyproject_path.parent / ".yaddd" / "layers.json"
    if candidate is None or not candidate.is_file():
        return {}
    try:
        raw = cast(dict[str, object], json.loads(candidate.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return {}
    if raw.get("schema") != 1:
        return {}
    layers = raw.get("layers", {})
    if not isinstance(layers, dict):
        return {}
    result: dict[str, LayerPolicy] = {}
    for name, value in cast(dict[str, object], layers).items():
        if not isinstance(value, dict):
            continue
        data = cast(dict[str, Any], value)
        result[str(name)] = LayerPolicy(
            imports=_as_str_set(data.get("imports")),
            third_party=_as_str_set(data.get("third_party")),
        )
    return result


def _find_pyproject(start: Path) -> Path | None:
    """Locate the nearest ``pyproject.toml`` by walking up from ``start``."""
    current = start.resolve()
    for parent in [current, *current.parents]:
        candidate = parent / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None
