"""Renderer that produces a Mermaid sequence diagram from scenarios."""

from __future__ import annotations

from yaddd_utils.inspect.scenario import ScenarioInfo
from yaddd_utils.mermaid._models import GraphModel, ScenarioEdge, ScenarioNode
from yaddd_utils.mermaid.renderers import RenderOptions
from yaddd_utils.mermaid.scenario import safe_id


class ScenarioSequenceRenderer:
    """Render scenario step flow as a Mermaid sequence diagram."""

    def __init__(self, options: RenderOptions | None = None) -> None:
        self._options = options or RenderOptions()

    def render(self, model: GraphModel) -> str:
        """Render ``model`` as a sequence diagram."""
        lines = ["sequenceDiagram"]
        actors: set[str] = set()
        for node in model.nodes:
            if node.scenario:
                actors.add(node.scenario)
        for actor in sorted(actors):
            lines.append(f"{self._options.indent}participant {actor}")
        current_actor: str | None = None
        for edge in model.edges:
            source_actor = self._actor_for(edge.source, model)
            target_actor = self._actor_for(edge.target, model)
            label = edge.label or "step"
            if source_actor and target_actor:
                lines.append(
                    f"{self._options.indent}{source_actor}->>{target_actor}: {label}"
                )
            elif source_actor and current_actor != source_actor:
                current_actor = source_actor
                lines.append(f"{self._options.indent}Note over {source_actor}: {label}")
        return "\n".join(lines)

    def render_infos(self, infos: list[ScenarioInfo]) -> str:
        """Build a sequence diagram from several scenarios."""
        return self.render(self.build_model(infos))

    def build_model(self, infos: list[ScenarioInfo]) -> GraphModel:
        """Create a GraphModel representing the sequence flow."""
        model = GraphModel(title="sequence")
        for info in infos:
            previous: str | None = None
            for step in info.steps:
                node_id = safe_id(f"{info.name}_{step.name}")
                model.add_node(
                    ScenarioNode(
                        id=node_id,
                        label=step.name,
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

    def _actor_for(self, node_id: str, model: GraphModel) -> str | None:
        for node in model.nodes:
            if node.id == node_id:
                return node.scenario
        return None
