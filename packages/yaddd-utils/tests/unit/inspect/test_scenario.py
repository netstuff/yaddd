import sys

from yaddd import Scenario, step
from yaddd_utils.inspect import ScenarioAnalyzer


class SampleScenario(Scenario[int]):
    @step
    async def first(self, ctx) -> int:
        return ctx.state + 1

    @step(when=lambda ctx: ctx.state > 0)
    async def second(self, ctx) -> int:
        return ctx.state + 10


class BranchingScenario(Scenario[int]):
    @step
    async def go(self, ctx) -> int:
        return ctx.state + 1


class EmptyScenario(Scenario[int]):
    pass


def test_analyzer_collects_steps_and_conditions():
    analyzer = ScenarioAnalyzer()
    info = analyzer.analyze_class(SampleScenario)

    assert info.name == "SampleScenario"
    assert len(info.steps) == 2
    assert info.steps[0].name == "first"
    assert info.steps[0].has_condition is False
    assert info.steps[1].name == "second"
    assert info.steps[1].has_condition is True


def test_analyzer_skips_empty_scenarios_when_scanning_module():
    analyzer = ScenarioAnalyzer()
    results = analyzer.analyze_module(sys.modules[__name__])

    names = {info.name for info in results}
    assert "SampleScenario" in names
    assert "BranchingScenario" in names
    assert "EmptyScenario" not in names
