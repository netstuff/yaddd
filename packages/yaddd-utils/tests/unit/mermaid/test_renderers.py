import sys

from yaddd import Scenario, step
from yaddd_utils.inspect import ScenarioAnalyzer
from yaddd_utils.mermaid import (
    RenderOptions,
    ScenarioGraphRenderer,
    ScenarioRenderer,
    ScenarioSequenceRenderer,
)


class DemoScenario(Scenario[int]):
    @step
    async def start(self, ctx) -> int:
        return ctx.state + 1

    @step(when=lambda ctx: ctx.state > 0)
    async def maybe(self, ctx) -> int:
        return ctx.state + 10


def _infos():
    return ScenarioAnalyzer().analyze_module(sys.modules[__name__])


def test_scenario_renderer_produces_flowchart():
    info = ScenarioAnalyzer().analyze_class(DemoScenario)
    renderer = ScenarioRenderer(RenderOptions(show_conditions=True))
    diagram = renderer.render_info(info)

    assert diagram.startswith("flowchart TD")
    assert "start" in diagram
    assert "maybe" in diagram


def test_graph_renderer_uses_subgraphs():
    infos = _infos()
    renderer = ScenarioGraphRenderer()
    diagram = renderer.render_infos(infos)

    assert diagram.startswith("flowchart TD")
    assert "subgraph DemoScenario" in diagram


def test_sequence_renderer_produces_sequence():
    infos = _infos()
    renderer = ScenarioSequenceRenderer()
    diagram = renderer.render_infos(infos)

    assert diagram.startswith("sequenceDiagram")
    assert "DemoScenario" in diagram
