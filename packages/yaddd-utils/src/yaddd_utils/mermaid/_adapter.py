"""Thin wrapper around ``mermaid-py`` with warning suppression."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any


class MermaidAdapterError(Exception):
    """mermaid-py interaction failed."""


def _import_mermaid() -> Any:
    """Import mermaid-py while suppressing its runtime warnings."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import mermaid  # type: ignore[import-untyped]

        return mermaid


def make_graph(title: str, script: str) -> Any:
    """Build a mermaid-py Graph object from a diagram script."""
    mermaid = _import_mermaid()
    graph_cls = mermaid.graph.Graph
    return graph_cls(title, script)


def save_image(script: str, output: Path | str, title: str = "yaddd") -> None:
    """Render ``script`` to an image file using mermaid-py.

    Supported extensions depend on the installed mermaid-py backend
    (``.png``, ``.svg`` and ``.pdf`` are common).
    """
    mermaid = _import_mermaid()
    graph = make_graph(title, script)
    renderer = mermaid.Mermaid(graph)
    path = Path(output)
    suffix = path.suffix.lower()
    if suffix == ".png":
        renderer.to_png(str(path))
    elif suffix == ".svg":
        renderer.to_svg(str(path))
    elif suffix == ".pdf":
        renderer.to_pdf(str(path))
    else:
        raise MermaidAdapterError(f"Unsupported image format: {suffix!r}")
