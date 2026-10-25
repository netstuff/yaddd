"""Dataclasses shared by Mermaid renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _empty_meta() -> dict[str, Any]:
    return {}


def _empty_nodes() -> list[ScenarioNode]:
    return []


def _empty_edges() -> list[ScenarioEdge]:
    return []


@dataclass(frozen=True, kw_only=True, slots=True)
class ScenarioNode:
    """A node in a scenario diagram."""

    id: str
    label: str
    scenario: str | None = None
    step: str | None = None
    shape: str = "round"
    meta: dict[str, Any] = field(default_factory=_empty_meta)


@dataclass(frozen=True, kw_only=True, slots=True)
class ScenarioEdge:
    """A directed edge between two scenario nodes."""

    source: str
    target: str
    label: str | None = None
    style: str | None = None


@dataclass(kw_only=True, slots=True)
class GraphModel:
    """Generic graph model produced by renderers."""

    title: str
    nodes: list[ScenarioNode] = field(default_factory=_empty_nodes)
    edges: list[ScenarioEdge] = field(default_factory=_empty_edges)

    def add_node(self, node: ScenarioNode) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: ScenarioEdge) -> None:
        self.edges.append(edge)
