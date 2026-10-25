"""Registry of inspection targets (modules and scenario classes)."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

from yaddd.application.handlers.scenarios import Scenario


def _empty_modules() -> set[str]:
    return set()


def _empty_classes() -> set[str]:
    return set()


@dataclass(kw_only=True, slots=True)
class TargetRegistry:
    """Collect modules and scenario classes to be inspected together."""

    _modules: set[str] = field(default_factory=_empty_modules)
    _classes: set[str] = field(default_factory=_empty_classes)

    def register_module(self, module: str | ModuleType) -> None:
        """Add a module to the inspection set."""
        name = module if isinstance(module, str) else module.__name__
        self._modules.add(name)

    def register_class(self, scenario_cls: type[Scenario[Any]]) -> None:
        """Add a scenario class to the inspection set."""
        self._classes.add(scenario_cls.__module__ + ":" + scenario_cls.scenario_name())

    def modules(self) -> Iterator[str]:
        """Yield all registered module names."""
        yield from sorted(self._modules)

    def classes(self) -> Iterator[str]:
        """Yield all registered class selectors in ``module:ClassName`` form."""
        yield from sorted(self._classes)

    def resolve_classes(self) -> Iterator[type[Scenario[Any]]]:
        """Import and yield registered scenario classes."""
        for selector in self._classes:
            module_name, class_name = selector.split(":", 1)
            module = importlib.import_module(module_name)
            yield getattr(module, class_name)
