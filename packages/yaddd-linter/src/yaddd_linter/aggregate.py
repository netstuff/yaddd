"""Aggregate and entity detection helpers."""

from __future__ import annotations

import ast
from pathlib import Path

AGGREGATE_BASES = frozenset({"AggregateRoot", "Entity"})


def is_aggregate_classdef(node: ast.ClassDef) -> bool:
    """Return True if the class definition inherits from AggregateRoot/Entity."""
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in AGGREGATE_BASES:
            return True
        # yaddd.domain.entities.AggregateRoot
        if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
            if base.attr in AGGREGATE_BASES:
                return True
    return False


def find_aggregate_classes(path: Path) -> set[str]:
    """Return a set of aggregate/entity class names defined in the file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return set()

    aggregates: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and is_aggregate_classdef(node):
            aggregates.add(node.name)
    return aggregates
