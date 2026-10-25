"""Base renderer protocol and shared options."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from yaddd_utils.inspect.scenario import ScenarioInfo
from yaddd_utils.mermaid._models import GraphModel


@dataclass(frozen=True, kw_only=True, slots=True)
class RenderOptions:
    """Common options for Mermaid renderers."""

    direction: str = "TD"
    show_conditions: bool = True
    show_levels: bool = False
    indent: str = "    "


class Renderer(Protocol):
    """Protocol for objects that render scenario models to Mermaid text."""

    def render(self, model: GraphModel) -> str:
        """Render ``model`` as a Mermaid diagram string."""
        ...

    def render_infos(self, infos: list[ScenarioInfo]) -> str:
        """Render a list of ScenarioInfo objects as a Mermaid diagram string."""
        ...
