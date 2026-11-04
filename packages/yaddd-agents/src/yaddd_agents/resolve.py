"""Rule resolution across base, extension and local packs."""

from __future__ import annotations

import importlib.metadata
import re
from typing import TYPE_CHECKING, Any

from yaddd_agents.model import (
    LAYERS,
    Operation,
    Pack,
    Project,
    Resolution,
    ResolvedRule,
    ResolveError,
    is_layer,
    normalize_name,
)

if TYPE_CHECKING:
    from yaddd_agents.model import Rule


_SPECIFIER = re.compile(r"^(>=|<=|==|!=|>|<|~=)\s*([0-9][0-9A-Za-z.*+!-]*)$")
_VERSION_PART = re.compile(r"[0-9]+")


def resolve(project: Project, packs: tuple[Pack, ...], local_operations: tuple[Operation, ...]) -> Resolution:
    """Resolve all rules, applying packs in order and letting deny win."""
    rules: dict[str, ResolvedRule] = {}
    for pack in packs:
        for rule in pack.rules:
            if rule.id in rules:
                raise ResolveError(f"Rule {rule.id!r} is declared twice; first by {rules[rule.id].sources[0]}")
            resolved = _resolved_from_rule(rule, pack)
            rules[rule.id] = resolved

    for pack in packs:
        for operation in pack.operations:
            _apply_operation(project, rules, operation)

    for operation in local_operations:
        _apply_operation(project, rules, operation)

    return Resolution(packs=packs, rules=rules)


def _resolved_from_rule(rule: Rule, pack: Pack) -> ResolvedRule:
    """Create the mutable resolved form of a declared rule."""
    docs = [f"{pack.name}/{rule.doc}"] if rule.doc else []
    return ResolvedRule(
        id=rule.id,
        layer=rule.layer,
        kind=rule.kind,
        docs=docs,
        allow_first_party=set(rule.allow_first_party),
        allow_third_party=set(rule.allow_third_party),
        deny_first_party=set(rule.deny_first_party),
        deny_third_party=set(rule.deny_third_party),
        enabled=rule.enabled,
        sources=[pack.name],
    )


def _apply_operation(project: Project, rules: dict[str, ResolvedRule], operation: Operation) -> None:
    """Apply one operation if its ``when`` condition holds."""
    if not _condition_holds(project, operation):
        return
    rule = rules.get(operation.rule)
    if rule is None:
        raise ResolveError(f"{operation.source}: operation references unknown rule {operation.rule!r}")

    if operation.kind == "relax":
        _add_values(rule.allow_first_party, rule.allow_third_party, operation.allow_add)
        if operation.allow_first_party is not None:
            rule.allow_first_party.update(operation.allow_first_party)
        if operation.allow_third_party is not None:
            rule.allow_third_party.update(operation.allow_third_party)
    elif operation.kind == "restrict":
        _add_values(rule.deny_first_party, rule.deny_third_party, operation.deny_add)
        if operation.deny_first_party is not None:
            rule.deny_first_party.update(operation.deny_first_party)
        if operation.deny_third_party is not None:
            rule.deny_third_party.update(operation.deny_third_party)
    elif operation.kind == "replace":
        if operation.allow_first_party is not None:
            rule.allow_first_party = set(operation.allow_first_party)
        if operation.allow_third_party is not None:
            rule.allow_third_party = set(operation.allow_third_party)
        if operation.deny_first_party is not None:
            rule.deny_first_party = set(operation.deny_first_party)
        if operation.deny_third_party is not None:
            rule.deny_third_party = set(operation.deny_third_party)
    elif operation.kind == "disable":
        rule.enabled = False
    else:
        raise ResolveError(f"{operation.source}: unknown operation {operation.kind!r}")

    rule.sources.append(f"{operation.source}:{operation.kind}")


def _add_values(first_party: set[str], third_party: set[str], values: frozenset[str]) -> None:
    """Classify values into first-party layers and third-party packages."""
    for value in values:
        if is_layer(value):
            first_party.add(value)
        else:
            third_party.add(value)


def _condition_holds(project: Project, operation: Operation) -> bool:
    """Evaluate a ``when = { dependency, specifier }`` condition."""
    if operation.when_dependency is None:
        return True
    requirement = project.dependencies.get(operation.when_dependency)
    if requirement is None:
        return False
    if operation.when_specifier is None:
        return True
    version = _installed_version(operation.when_dependency)
    if version is None:
        return True
    return _satisfies(version, operation.when_specifier)


def _installed_version(name: str) -> str | None:
    """Return the installed version of a distribution, if available."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _satisfies(version: str, specifier: str) -> bool:
    """Check a small, dependency-free subset of PEP 440 version specifiers."""
    for raw_part in specifier.split(","):
        part = raw_part.strip()
        if not part:
            continue
        match = _SPECIFIER.match(part)
        if match is None:
            continue
        operator, target = match.groups()
        current_tuple = _version_tuple(version)
        target_tuple = _version_tuple(target)
        if operator == ">=" and not current_tuple >= target_tuple:
            return False
        if operator == "<=" and not current_tuple <= target_tuple:
            return False
        if operator == ">" and not current_tuple > target_tuple:
            return False
        if operator == "<" and not current_tuple < target_tuple:
            return False
        if operator == "==" and not current_tuple == target_tuple:
            return False
        if operator == "!=" and current_tuple == target_tuple:
            return False
        if operator == "~=" and not _compatible(current_tuple, target_tuple):
            return False
    return True


def _version_tuple(version: str) -> tuple[int, ...]:
    """Turn a version string into a comparable integer tuple."""
    parts = _VERSION_PART.findall(version)
    return tuple(int(part) for part in parts[:4]) or (0,)


def _compatible(current: tuple[int, ...], target: tuple[int, ...]) -> bool:
    """Approximate ``~=`` compatibility for the common ``~=X.Y`` form."""
    if not current or not target or not current >= target:
        return False
    if len(target) < 2:
        return current[:1] == target[:1]
    return current[: len(target) - 1] == target[: len(target) - 1]


def layers_config(resolution: Resolution) -> dict[str, object]:
    """Build the machine-readable layer policy consumed by yaddd-linter."""
    layers: dict[str, dict[str, list[str]]] = {}
    for layer in LAYERS:
        rule = resolution.rules.get(f"IMPORTS_{layer.upper()}")
        if rule is None or not rule.enabled:
            continue
        layers[layer] = {
            "imports": sorted(rule.effective_first_party),
            "third_party": sorted(rule.effective_third_party),
        }
    return {
        "schema": 1,
        "generated_by": "yaddd-agents",
        "layers": layers,
    }


def explain(resolution: Resolution, rule_id: str) -> dict[str, Any]:
    """Render one resolved rule for ``explain`` output."""
    rule = resolution.rules.get(rule_id)
    if rule is None:
        raise ResolveError(f"Unknown rule {rule_id!r}")
    return {
        "id": rule.id,
        "layer": rule.layer,
        "kind": rule.kind,
        "enabled": rule.enabled,
        "allow_first_party": sorted(rule.allow_first_party),
        "allow_third_party": sorted(rule.allow_third_party),
        "deny_first_party": sorted(rule.deny_first_party),
        "deny_third_party": sorted(rule.deny_third_party),
        "effective_first_party": sorted(rule.effective_first_party),
        "effective_third_party": sorted(rule.effective_third_party),
        "sources": rule.sources,
        "docs": rule.docs,
    }


def pack_summary(packs: tuple[Pack, ...]) -> list[dict[str, str]]:
    """Return a machine-readable list of active packs."""
    return [
        {
            "name": pack.name,
            "version": pack.version,
            "manifest": str(pack.manifest_path),
        }
        for pack in packs
    ]


def dependency_names(project: Project) -> list[str]:
    """Return normalized project dependency names."""
    return sorted(normalize_name(name) for name in project.dependencies)
