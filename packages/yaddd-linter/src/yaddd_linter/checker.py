"""AST-based linters for yaddd projects."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

from yaddd_linter.aggregate import find_aggregate_classes, is_aggregate_classdef
from yaddd_linter.layers import (
    ALLOWED_IMPORTS,
    UNKNOWN,
    layer_from_module,
    layer_from_path,
    package_root_from_path,
)
from yaddd_linter.rules import Rule, Violation

_STDLIB_NAMES: frozenset[str] = frozenset(sys.stdlib_module_names)

# Third-party modules the domain layer may import besides ``yaddd`` itself.
# Value objects are built on ``PydanticVO`` — "subclass PydanticVO in your
# domain" is documented plugin behaviour — and their constraints are declared
# with ``pydantic.Field``, so the serialization stack is part of the domain's
# toolkit even though the plugin's own sources live in infrastructure.
_DOMAIN_ALLOWED_THIRD_PARTY: frozenset[str] = frozenset({"pydantic", "yaddd_pydantic"})


def _is_stdlib(module_name: str) -> bool:
    """Return True if the module is part of the Python standard library."""
    top = module_name.split(".")[0]
    return top in _STDLIB_NAMES


def _is_first_party(module_name: str, package_root: str | None = None) -> bool:
    """Return True if the module belongs to the project being linted.

    ``yaddd`` itself and every module under the project's own module root
    (``app`` in a flat layout, ``src/<package>`` in a src layout) count as
    first-party; anything else (including third-party packages) does not.
    """
    top = module_name.split(".")[0]
    if top == "yaddd":
        return True
    return package_root is not None and top == package_root


def _plugin_name(path: Path) -> str | None:
    """Return the plugin package name for files under yaddd_sqlalchemy/yaddd_pydantic."""
    parts = path.parts
    if "yaddd_sqlalchemy" in parts:
        return "yaddd_sqlalchemy"
    if "yaddd_pydantic" in parts:
        return "yaddd_pydantic"
    return None


def _imported_plugin(module_name: str) -> str | None:
    """Return the plugin package name if the imported module is a yaddd plugin."""
    top = module_name.split(".")[0]
    if top in {"yaddd_sqlalchemy", "yaddd_pydantic"}:
        return top
    return None


def _extract_module_name(alias: ast.alias) -> str | None:
    """Return the canonical module name from an import alias."""
    if alias.name:
        return alias.name
    return None


def _is_aggregate_type(name: str, aggregates: set[str]) -> bool:
    """Return True if the given type name refers to a known aggregate/entity."""
    if name in aggregates:
        return True
    # Handle yaddd.domain.entities.AggregateRoot style references lazily.
    if "." in name:
        return name.split(".")[-1] in aggregates
    return False


def _annotation_name(node: ast.expr | None) -> str | None:
    """Extract a simple name from a type annotation node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.expr = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return None


class LayerIsolationChecker(Rule):
    """Ensure dependency direction between architectural layers."""

    def check(self, path: Path, source: str) -> list[Violation]:
        violations: list[Violation] = []
        current_layer = layer_from_path(path)
        if current_layer is UNKNOWN:
            return violations

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = _extract_module_name(alias)
                    if module is None:
                        continue
                    violations.extend(self._check_import(path, node.lineno, node.col_offset, current_layer, module))
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                # Relative imports are only checked if they cross layer boundaries.
                if node.level and node.level > 0:
                    imported_layer = layer_from_module(node.module)
                    if imported_layer is UNKNOWN:
                        continue
                    if imported_layer in ALLOWED_IMPORTS.get(current_layer, set()):
                        continue
                    # Same-layer relative imports are allowed.
                    if imported_layer == current_layer:
                        continue
                    violations.append(
                        Violation(
                            str(path),
                            node.lineno,
                            node.col_offset,
                            "YDDD003",
                            f"{current_layer} layer relative-imports from disallowed layer: {node.module}",
                        )
                    )
                    continue
                module = node.module
                violations.extend(self._check_import(path, node.lineno, node.col_offset, current_layer, module))
        return violations

    def _check_import(
        self,
        path: Path,
        line: int,
        col: int,
        current_layer: Any,
        module: str,
    ) -> list[Violation]:
        if module == "__future__" or _is_stdlib(module):
            return []

        # YDDD005: plugins must not import each other.
        current_plugin = _plugin_name(path)
        imported_plugin = _imported_plugin(module)
        if current_plugin is not None and imported_plugin is not None and current_plugin != imported_plugin:
            return [
                Violation(
                    str(path),
                    line,
                    col,
                    "YDDD005",
                    f"Plugin {current_plugin!r} imports another plugin: {imported_plugin!r}",
                )
            ]

        # The domain layer may always use the serialization stack: its
        # value-object bases are domain classes (see
        # _DOMAIN_ALLOWED_THIRD_PARTY), so neither YDDD004 (third-party) nor
        # YDDD003 (wrong layer) applies.
        if current_layer.name == "domain" and module.split(".")[0] in _DOMAIN_ALLOWED_THIRD_PARTY:
            return []

        # YDDD004: domain layer must depend only on stdlib and first-party modules.
        if current_layer.name == "domain" and not _is_first_party(module, package_root_from_path(path)):
            return [
                Violation(
                    str(path),
                    line,
                    col,
                    "YDDD004",
                    f"Domain layer imports third-party module: {module!r}",
                )
            ]

        imported_layer = layer_from_module(module)
        if imported_layer is UNKNOWN:
            return []
        if imported_layer in ALLOWED_IMPORTS.get(current_layer, set()):
            return []
        return [
            Violation(
                str(path),
                line,
                col,
                "YDDD003",
                f"{current_layer} layer imports from {imported_layer} layer: {module!r}",
            )
        ]


class AggregateMutationChecker(Rule):
    """Detect direct mutation of aggregate/entity fields outside their own methods."""

    def __init__(self, aggregate_names: set[str]) -> None:
        self.aggregate_names = aggregate_names

    def check(self, path: Path, source: str) -> list[Violation]:
        violations: list[Violation] = []
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return violations

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                violations.extend(self._check_class(path, node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                violations.extend(self._check_function(path, node, False, ""))
        return violations

    def _check_class(self, path: Path, class_node: ast.ClassDef) -> list[Violation]:
        violations: list[Violation] = []
        class_is_aggregate = is_aggregate_classdef(class_node)

        for item in class_node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            violations.extend(self._check_function(path, item, class_is_aggregate, class_node.name))
        return violations

    def _check_function(
        self,
        path: Path,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        class_is_aggregate: bool,
        class_name: str,
    ) -> list[Violation]:
        violations: list[Violation] = []
        local_types: dict[str, str] = {}

        if class_is_aggregate:
            # The first positional argument in a method is 'self' and its type is the aggregate.
            local_types["self"] = class_name

        # Collect types from annotated arguments.
        for arg in func.args.args + func.args.kwonlyargs:
            ann = _annotation_name(arg.annotation)
            if ann and _is_aggregate_type(ann, self.aggregate_names):
                local_types[arg.arg] = ann

        # Collect types from annotated assignments in the function body.
        for node in ast.walk(func):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                ann = _annotation_name(node.annotation)
                if ann:
                    local_types[node.target.id] = ann

        # Collect types from constructor calls and aggregate-returning calls.
        for node in ast.walk(func):
            if isinstance(node, ast.Assign):
                value_name = _annotation_name(node.value)
                if not value_name and isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        value_name = node.value.func.id
                    elif isinstance(node.value.func, ast.Attribute):
                        value_name = node.value.func.attr
                if value_name and _is_aggregate_type(value_name, self.aggregate_names):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            local_types[target.id] = value_name

        # Now check for mutations.
        for node in ast.walk(func):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
                for target in targets:
                    if isinstance(target, ast.Attribute):
                        violation = self._check_attribute_mutation(
                            path, target, local_types, class_is_aggregate, class_name
                        )
                        if violation:
                            violations.append(violation)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Attribute):
                violation = self._check_attribute_mutation(
                    path, node.target, local_types, class_is_aggregate, class_name
                )
                if violation:
                    violations.append(violation)
            elif isinstance(node, ast.Call):
                # Detect mutating calls on aggregate attributes, e.g. order.items.append(x).
                func_node = node.func
                if isinstance(func_node, ast.Attribute) and isinstance(func_node.value, ast.Attribute):
                    inner = func_node.value
                    if isinstance(inner.value, ast.Name):
                        var_name = inner.value.id
                        if var_name == "self" and class_is_aggregate:
                            continue
                        var_type = local_types.get(var_name)
                        if var_type and _is_aggregate_type(var_type, self.aggregate_names):
                            violations.append(
                                Violation(
                                    str(path),
                                    node.lineno,
                                    node.col_offset,
                                    "YDDD002",
                                    f"Mutating call on aggregate attribute '{inner.attr}' "
                                    f"of variable '{var_name}' outside aggregate methods",
                                )
                            )
        return violations

    def _check_attribute_mutation(
        self,
        path: Path,
        target: ast.Attribute,
        local_types: dict[str, str],
        class_is_aggregate: bool,
        class_name: str,
    ) -> Violation | None:
        if not isinstance(target.value, ast.Name):
            return None
        var_name = target.value.id
        if var_name == "self" and class_is_aggregate:
            return None
        var_type = local_types.get(var_name)
        if var_type and _is_aggregate_type(var_type, self.aggregate_names):
            return Violation(
                str(path),
                target.lineno,
                target.col_offset,
                "YDDD001",
                f"Direct mutation of aggregate field '{target.attr}' "
                f"of variable '{var_name}' outside aggregate methods",
            )
        return None


def collect_aggregate_names(paths: list[Path]) -> set[str]:
    """Scan the given paths and collect all aggregate/entity class names."""
    aggregates: set[str] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            aggregates.update(find_aggregate_classes(path))
        elif path.is_dir():
            for file in path.rglob("*.py"):
                aggregates.update(find_aggregate_classes(file))
    return aggregates
