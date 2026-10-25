"""Scenario introspection for yaddd application workflows."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Sequence
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, TypeVar

from yaddd.application.handlers.scenarios import Scenario, Step


T = TypeVar("T")


def _is_scenario_subclass(obj: Any) -> bool:
    return inspect.isclass(obj) and issubclass(obj, Scenario) and obj is not Scenario


@dataclass(frozen=True, kw_only=True, slots=True)
class StepInfo:
    """Introspected metadata of a single scenario step."""

    name: str
    method_name: str
    has_condition: bool = False
    branch_target: str | None = None
    level: str = "info"


@dataclass(frozen=True, kw_only=True, slots=True)
class ScenarioInfo:
    """Introspected metadata of a yaddd Scenario class."""

    name: str
    module: str
    steps: Sequence[StepInfo] = ()
    dependencies: Sequence[str] = field(default_factory=tuple)


class ScenarioAnalyzer:
    """Collect structural metadata from yaddd Scenario classes."""

    def analyze_module(self, module: str | ModuleType) -> list[ScenarioInfo]:
        """Inspect all Scenario subclasses declared in ``module``."""
        if isinstance(module, str):
            module = importlib.import_module(module)
        result: list[ScenarioInfo] = []
        for _name, obj in inspect.getmembers(module, _is_scenario_subclass):
            info = self.analyze_class(obj)
            if info.steps:
                result.append(info)
        return result

    def analyze_class(self, scenario_cls: type[Scenario[Any]]) -> ScenarioInfo:
        """Inspect a single Scenario subclass."""
        declared_steps: Sequence[Step[Any]] = getattr(scenario_cls, "_declared_steps", ())
        steps = [self._step_info(step) for step in declared_steps]
        return ScenarioInfo(
            name=scenario_cls.scenario_name(),
            module=scenario_cls.__module__,
            steps=steps,
            dependencies=self._constructor_params(scenario_cls),
        )

    def analyze_object(self, scenario: Scenario[Any]) -> ScenarioInfo:
        """Inspect a Scenario instance (same as its class)."""
        return self.analyze_class(type(scenario))

    def _step_info(self, step: Step[Any]) -> StepInfo:
        target: str | None = None
        if step.branch_to is not None:
            target = self._branch_target_name(step.branch_to)
        return StepInfo(
            name=step.name,
            method_name=step.method_name,
            has_condition=step.when is not None,
            branch_target=target,
            level=step.level,
        )

    def _branch_target_name(self, branch_to: Any) -> str | None:
        if inspect.isclass(branch_to) and issubclass(branch_to, Scenario):
            return branch_to.scenario_name()
        if callable(branch_to) and hasattr(branch_to, "__annotations__"):
            return getattr(branch_to, "__name__", None) or repr(branch_to)
        return None

    def _constructor_params(self, scenario_cls: type[Scenario[Any]]) -> Sequence[str]:
        signature = inspect.signature(scenario_cls.__init__)
        return [
            name
            for name, param in signature.parameters.items()
            if name != "self" and param.default is inspect.Parameter.empty
        ]
