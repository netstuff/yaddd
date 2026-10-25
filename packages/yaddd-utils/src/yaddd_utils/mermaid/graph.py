"""Renderer that groups scenario steps into per-scenario subgraphs."""

from __future__ import annotations

from yaddd_utils.inspect.scenario import ScenarioInfo
from yaddd_utils.mermaid._models import GraphModel, ScenarioEdge, ScenarioNode
from yaddd_utils.mermaid.renderers import RenderOptions
from yaddd_utils.mermaid.scenario import safe_id


class ScenarioGraphRenderer:
    """Render scenarios as a flowchart with a subgraph per scenario."""

    def __init__(self, options: RenderOptions | None = None) -> None:
        self._options = options or RenderOptions()

    def render(self, model: GraphModel) -> str:
        """Render ``model`` as a flowchart with subgraphs."""
        lines = [f"flowchart {self._options.direction}"]
        current_subgraph: str | None = None
        for node in model.nodes:
            if node.scenario and node.scenario != current_subgraph:
                if current_subgraph is not None:
                    lines.append(f"{self._options.indent}end")
                current_subgraph = node.scenario
                lines.append(f"{self._options.indent}subgraph {node.scenario}")
            lines.append(self._render_node(node))
        if current_subgraph is not None:
            lines.append(f"{self._options.indent}end")
        for edge in model.edges:
            lines.append(self._render_edge(edge))
        return "\n".join(lines)

    def render_infos(self, infos: list[ScenarioInfo]) -> str:
        """Build a grouped flowchart from several scenarios."""
        return self.render(self.build_model(infos))

    def build_model(self, infos: list[ScenarioInfo]) -> GraphModel:
        """Create a GraphModel from multiple ScenarioInfo objects."""
        model = GraphModel(title="scenarios")
        for info in infos:
            self._add_scenario(model, info)
        return model

    def _add_scenario(self, model: GraphModel, info: ScenarioInfo) -> None:
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

    def _render_node(self, node: ScenarioNode) -> str:
        label = node.label.replace('"', '"')
        return f'{self._options.indent}{node.id}("{label}")'

    def _render_edge(self, edge: ScenarioEdge) -> str:
        if edge.label:
            return f"{self._options.indent}{edge.source} -->|{edge.label}| {edge.target}"
        return f"{self._options.indent}{edge.source} --> {edge.target}"
