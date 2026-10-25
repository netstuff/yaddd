"""Renderer that turns a single scenario into a Mermaid flowchart."""

from __future__ import annotations

from yaddd_utils.inspect.scenario import ScenarioInfo
from yaddd_utils.mermaid._models import GraphModel, ScenarioEdge, ScenarioNode
from yaddd_utils.mermaid.renderers import RenderOptions


def safe_id(name: str) -> str:
    """Produce a Mermaid-safe node identifier."""
    return "".join(ch if ch.isalnum() else "_" for ch in name)


class ScenarioRenderer:
    """Render one or more ScenarioInfo objects as a flat flowchart."""

    def __init__(self, options: RenderOptions | None = None) -> None:
        self._options = options or RenderOptions()

    def render(self, model: GraphModel) -> str:
        """Render ``model`` as a Mermaid flowchart."""
        lines = [f"flowchart {self._options.direction}"]
        for node in model.nodes:
            lines.append(self._render_node(node))
        for edge in model.edges:
            lines.append(self._render_edge(edge))
        return "\n".join(lines)

    def render_info(self, info: ScenarioInfo) -> str:
        """Build a flowchart for a single scenario."""
        return self.render(self.build_model(info))

    def render_infos(self, infos: list[ScenarioInfo]) -> str:
        """Build a flat flowchart for multiple scenarios."""
        if len(infos) == 1:
            return self.render_info(infos[0])
        parts = [self.render_info(info) for info in infos]
        return "\n\n".join(parts)

    def build_model(self, info: ScenarioInfo) -> GraphModel:
        """Create a GraphModel from a single ScenarioInfo."""
        model = GraphModel(title=info.name)
        previous: str | None = None
        for step in info.steps:
            node_id = safe_id(f"{info.name}_{step.name}")
            label = step.name
            if self._options.show_levels:
                label = f"[{step.level}] {label}"
            if step.has_condition and self._options.show_conditions:
                label = f"{label} ❓"
            model.add_node(
                ScenarioNode(
                    id=node_id,
                    label=label,
                    scenario=info.name,
                    step=step.name,
                )
            )
            if previous is not None:
                model.add_edge(ScenarioEdge(source=previous, target=node_id))
            if step.branch_target is not None:
                target_id = safe_id(step.branch_target)
                model.add_node(ScenarioNode(id=target_id, label=step.branch_target))
                model.add_edge(
                    ScenarioEdge(
                        source=node_id,
                        target=target_id,
                        label="branch",
                    )
                )
            previous = node_id
        return model

    def _render_node(self, node: ScenarioNode) -> str:
        label = node.label.replace('"', '"')
        if node.shape == "round":
            return f'{self._options.indent}{node.id}("{label}")'
        if node.shape == "diamond":
            return f'{self._options.indent}{node.id}{{"{label}"}}'
        return f'{self._options.indent}{node.id}["{label}"]'

    def _render_edge(self, edge: ScenarioEdge) -> str:
        if edge.label:
            return f"{self._options.indent}{edge.source} -->|{edge.label}| {edge.target}"
        return f"{self._options.indent}{edge.source} --> {edge.target}"
