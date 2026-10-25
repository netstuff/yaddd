"""Renderer that turns State subclasses into Mermaid state diagrams."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from yaddd_utils.mermaid._models import GraphModel, ScenarioNode
from yaddd_utils.mermaid.renderers import RenderOptions


class ScenarioStateRenderer:
    """Render a yaddd State subclass as a Mermaid state diagram."""

    def __init__(self, options: RenderOptions | None = None) -> None:
        self._options = options or RenderOptions()

    def render(self, model: GraphModel) -> str:
        """Render ``model`` as a state diagram."""
        lines = ["stateDiagram-v2"]
        for node in model.nodes:
            lines.append(f"{self._options.indent}[*] --> {node.id} : initialize")
            lines.append(f"{self._options.indent}{node.id} : {node.label}")
        return "\n".join(lines)

    def render_state_class(self, state_cls: type[Any]) -> str:
        """Build a state diagram for a single State subclass."""
        return self.render(self.build_model(state_cls))

    def build_model(self, state_cls: type[Any]) -> GraphModel:
        """Create a GraphModel from a State subclass."""
        title = getattr(state_cls, "__qualname__", "State")
        model = GraphModel(title=title)
        fields: Sequence[str] = getattr(state_cls, "_fields", ())
        for name in fields:
            model.add_node(
                ScenarioNode(
                    id=name,
                    label=name,
                    scenario=title,
                )
            )
        return model
