"""Project and pack discovery."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import re
import tomllib
from pathlib import Path
from typing import Any, cast

from yaddd_agents.model import (
    SCHEMA_VERSION,
    DiscoveryError,
    ManifestError,
    Operation,
    Pack,
    Project,
    Rule,
    normalize_name,
)

_REQUIREMENT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*")
_SKIP_DEPENDENCIES = frozenset({"yaddd", "yaddd-agents", "yaddd-linter"})


def find_project_root(start: Path) -> Path:
    """Walk up from ``start`` until a ``pyproject.toml`` is found."""
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise DiscoveryError(f"No pyproject.toml found above {start}")


def load_project(root: Path | None = None) -> Project:
    """Load the project description needed for pack discovery."""
    project_root = find_project_root(root or Path.cwd())
    pyproject_path = project_root / "pyproject.toml"
    try:
        raw = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise DiscoveryError(f"Cannot read {pyproject_path}: {exc}") from exc

    dependencies = _collect_dependencies(raw)
    tool = cast(dict[str, Any], raw.get("tool", {}))
    agents = cast(dict[str, Any], tool.get("yaddd", {}).get("agents", {}))
    extensions = cast(dict[str, Any], agents.get("extensions", {}))
    extension_paths = {str(name): str(path) for name, path in extensions.items()}
    return Project(
        root=project_root,
        pyproject_path=pyproject_path,
        dependencies=dependencies,
        extension_paths=extension_paths,
    )


def _collect_dependencies(raw: dict[str, Any]) -> dict[str, str]:
    """Collect runtime and development dependencies from pyproject.toml."""
    collected: dict[str, str] = {}
    project = cast(dict[str, Any], raw.get("project", {}))
    _add_requirements(collected, project.get("dependencies", []))
    optional = cast(dict[str, Any], project.get("optional-dependencies", {}))
    for requirements in optional.values():
        _add_requirements(collected, requirements)

    groups = cast(dict[str, Any], raw.get("dependency-groups", {}))
    _collect_groups(collected, groups, set())
    return collected


def _collect_groups(collected: dict[str, str], groups: dict[str, Any], seen: set[str]) -> None:
    """Collect dependency-group entries, following ``include-group``."""
    for name, entries in groups.items():
        if name in seen:
            continue
        seen.add(name)
        if not isinstance(entries, list):
            continue
        for entry in cast(list[Any], entries):
            if isinstance(entry, str):
                _add_requirements(collected, [entry])
            elif isinstance(entry, dict):
                data = cast(dict[str, object], entry)
                if "include-group" not in data:
                    continue
                included = str(data["include-group"])
                nested = groups.get(included)
                if isinstance(nested, list):
                    _collect_groups(collected, {included: nested}, seen)


def _add_requirements(collected: dict[str, str], requirements: Any) -> None:
    """Add requirement strings to a normalized name -> requirement mapping."""
    if not isinstance(requirements, list):
        return
    for requirement in cast(list[Any], requirements):
        if not isinstance(requirement, str):
            continue
        match = _REQUIREMENT_NAME.match(requirement.strip())
        if match is None:
            continue
        name = normalize_name(match.group(0))
        collected.setdefault(name, requirement.strip())


def load_pack(manifest_path: Path, source: str = "") -> Pack:
    """Load one pack manifest and its Markdown resources."""
    try:
        raw = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"Cannot read {manifest_path}: {exc}") from exc

    schema = raw.get("schema")
    if schema != SCHEMA_VERSION:
        raise ManifestError(f"{manifest_path}: unsupported schema {schema!r}; expected {SCHEMA_VERSION}")

    name = str(raw.get("name") or manifest_path.parent.parent.name)
    version = str(raw.get("version") or "0.0.0")
    core_doc = str(raw.get("core") or "")
    docs = _load_docs(manifest_path.parent)
    rules = _parse_rules(raw, manifest_path, docs)
    operations = _parse_operations(raw, source or name)
    return Pack(
        name=name,
        version=version,
        manifest_path=manifest_path,
        rules=tuple(rules),
        operations=tuple(operations),
        docs=docs,
        core_doc=core_doc,
    )


def _load_docs(base_dir: Path) -> dict[str, str]:
    """Load every Markdown file below ``base_dir/rules``."""
    rules_dir = base_dir / "rules"
    if not rules_dir.is_dir():
        return {}
    docs: dict[str, str] = {}
    for path in sorted(rules_dir.rglob("*.md")):
        docs[path.relative_to(base_dir).as_posix()] = path.read_text(encoding="utf-8")
    return docs


def _parse_rules(raw: dict[str, Any], manifest_path: Path, docs: dict[str, str]) -> list[Rule]:
    """Parse the ``[rules.<ID>]`` tables."""
    rules_raw = raw.get("rules", {})
    if not isinstance(rules_raw, dict):
        raise ManifestError(f"{manifest_path}: [rules] must be a table")
    rules: list[Rule] = []
    for rule_id, value in cast(dict[str, Any], rules_raw).items():
        if not isinstance(value, dict):
            raise ManifestError(f"{manifest_path}: rule {rule_id!r} must be a table")
        data = cast(dict[str, Any], value)
        layer = str(data.get("layer") or "")
        if not layer:
            raise ManifestError(f"{manifest_path}: rule {rule_id!r} has no layer")
        doc = str(data.get("doc") or "")
        if doc and doc not in docs:
            raise ManifestError(f"{manifest_path}: rule {rule_id!r} references missing doc {doc!r}")
        rules.append(
            Rule(
                id=rule_id,
                layer=layer,
                kind=str(data.get("kind") or "guidance"),
                doc=doc,
                allow_first_party=_string_set(data.get("allow_first_party")),
                allow_third_party=_string_set(data.get("allow_third_party")),
                deny_first_party=_string_set(data.get("deny_first_party")),
                deny_third_party=_string_set(data.get("deny_third_party")),
                enabled=bool(data.get("enabled", True)),
            )
        )
    return rules


def _parse_operations(raw: dict[str, Any], source: str) -> list[Operation]:
    """Parse relax/restrict/replace/disable arrays."""
    operations: list[Operation] = []
    for kind, key in (
        ("relax", "relaxes"),
        ("restrict", "restricts"),
        ("replace", "replaces"),
        ("disable", "disables"),
    ):
        entries = raw.get(key, [])
        if not isinstance(entries, list):
            raise ManifestError(f"{source}: {key} must be an array of tables")
        for entry in cast(list[Any], entries):
            if not isinstance(entry, dict):
                raise ManifestError(f"{source}: {key} entries must be tables")
            operations.append(_parse_operation(kind, cast(dict[str, Any], entry), source))
    return operations


def _parse_operation(kind: str, data: dict[str, Any], source: str) -> Operation:
    """Parse one operation table."""
    rule = str(data.get("rule") or "")
    reason = str(data.get("reason") or "")
    if not rule:
        raise ManifestError(f"{source}: {kind} operation has no rule")
    if not reason:
        raise ManifestError(f"{source}: {kind} operation for {rule!r} has no reason")
    when = data.get("when", {})
    if not isinstance(when, dict):
        raise ManifestError(f"{source}: {kind} operation for {rule!r} has invalid when")
    when_data = cast(dict[str, Any], when)
    dependency = when_data.get("dependency")
    specifier = when_data.get("specifier")
    return Operation(
        kind=kind,
        rule=rule,
        reason=reason,
        allow_add=_string_set(data.get("allow_add")),
        deny_add=_string_set(data.get("deny_add")),
        allow_first_party=_optional_string_set(data, "allow_first_party"),
        allow_third_party=_optional_string_set(data, "allow_third_party"),
        deny_first_party=_optional_string_set(data, "deny_first_party"),
        deny_third_party=_optional_string_set(data, "deny_third_party"),
        when_dependency=normalize_name(str(dependency)) if dependency else None,
        when_specifier=str(specifier) if specifier else None,
        source=source,
    )


def _string_set(value: Any) -> frozenset[str]:
    """Coerce a list of strings into a frozen set."""
    if not isinstance(value, list):
        return frozenset()
    return frozenset(str(item) for item in cast(list[Any], value))


def _optional_string_set(data: dict[str, Any], key: str) -> frozenset[str] | None:
    """Return a frozen set for a key, or None when the key is absent."""
    if key not in data:
        return None
    return _string_set(data.get(key))


def discover_packs(project: Project, workspace_root: Path | None = None) -> tuple[Pack, ...]:
    """Discover the base pack and every active extension pack."""
    base_path = Path(__file__).resolve().parent / "resources" / "base" / "manifest.toml"
    packs: list[Pack] = [load_pack(base_path, source="base")]
    seen = {normalize_name(packs[0].name)}

    for name, path in sorted(project.extension_paths.items()):
        manifest = (project.root / path).resolve()
        if not manifest.is_file():
            raise DiscoveryError(f"Explicit extension {name!r} points to missing {manifest}")
        pack = load_pack(manifest, source=f"explicit:{name}")
        _append_pack(packs, seen, pack)

    for dependency in sorted(project.dependencies):
        if dependency in _SKIP_DEPENDENCIES or not dependency.startswith("yaddd-"):
            continue
        manifest = None
        if workspace_root is not None:
            manifest = _workspace_manifest(dependency, workspace_root)
        if manifest is None:
            manifest = _installed_manifest(dependency)
        if manifest is None:
            continue
        pack = load_pack(manifest, source=f"dependency:{dependency}")
        _append_pack(packs, seen, pack)

    return tuple(packs)


def _append_pack(packs: list[Pack], seen: set[str], pack: Pack) -> None:
    """Append a pack unless one with the same normalized name is already loaded."""
    key = normalize_name(pack.name)
    if key in seen:
        return
    seen.add(key)
    packs.append(pack)


def _workspace_manifest(name: str, workspace_root: Path) -> Path | None:
    """Find a pack manifest in a monorepo workspace."""
    module = normalize_name(name).replace("-", "_")
    matches = sorted(workspace_root.glob(f"packages/*/src/{module}/agents/manifest.toml"))
    if matches:
        return matches[0]
    candidate = workspace_root / "packages" / name / "src" / module / "agents" / "manifest.toml"
    return candidate if candidate.is_file() else None


def _installed_manifest(name: str) -> Path | None:
    """Find a pack manifest inside an installed or editable distribution."""
    module = normalize_name(name).replace("-", "_")
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        spec = None
    if spec is not None and spec.submodule_search_locations:
        candidate = Path(next(iter(spec.submodule_search_locations))) / "agents" / "manifest.toml"
        if candidate.is_file():
            return candidate

    try:
        distribution = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return None
    candidate = cast(Path, distribution.locate_file(f"{module}/agents/manifest.toml"))
    return candidate if candidate.is_file() else None


def load_local_operations(project: Project) -> tuple[Operation, ...]:
    """Load hand-written local overrides, if any."""
    path = project.overrides_path
    if not path.is_file():
        return ()
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"Cannot read {path}: {exc}") from exc
    return tuple(_parse_operations(raw, source="local"))
