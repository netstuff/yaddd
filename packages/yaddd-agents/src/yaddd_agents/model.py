"""Data model shared by discovery, resolution and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_VERSION = 1
LAYERS: tuple[str, ...] = ("domain", "application", "infrastructure", "presentation", "testing", "tooling")
MANAGED_BEGIN = "<!-- yaddd-agents:begin -->"
MANAGED_END = "<!-- yaddd-agents:end -->"


class AgentsError(Exception):
    """Base error for user-facing yaddd-agents failures."""


class DiscoveryError(AgentsError):
    """A project or pack could not be discovered."""


class ManifestError(AgentsError):
    """A manifest is invalid."""


class ResolveError(AgentsError):
    """Rules cannot be resolved."""


def normalize_name(name: str) -> str:
    """Return the PEP 503 normalized distribution name."""
    return name.strip().lower().replace("_", "-").replace(".", "-")


def is_layer(value: str) -> bool:
    """Return True when a value names an architectural layer."""
    return value in LAYERS


@dataclass(frozen=True, slots=True)
class Rule:
    """A rule declared by a pack."""

    id: str
    layer: str
    kind: str = "guidance"
    doc: str = ""
    allow_first_party: frozenset[str] = frozenset()
    allow_third_party: frozenset[str] = frozenset()
    deny_first_party: frozenset[str] = frozenset()
    deny_third_party: frozenset[str] = frozenset()
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class Operation:
    """A pack's request to relax, restrict, replace or disable a rule."""

    kind: str
    rule: str
    reason: str
    allow_add: frozenset[str] = frozenset()
    deny_add: frozenset[str] = frozenset()
    allow_first_party: frozenset[str] | None = None
    allow_third_party: frozenset[str] | None = None
    deny_first_party: frozenset[str] | None = None
    deny_third_party: frozenset[str] | None = None
    when_dependency: str | None = None
    when_specifier: str | None = None
    source: str = ""


@dataclass(frozen=True, slots=True)
class Pack:
    """A loaded pack: base, extension or local overrides."""

    name: str
    version: str
    manifest_path: Path
    rules: tuple[Rule, ...] = ()
    operations: tuple[Operation, ...] = ()
    docs: dict[str, str] = field(default_factory=dict[str, str])
    core_doc: str = ""


@dataclass(slots=True)
class ResolvedRule:
    """A rule after every active pack has been applied."""

    id: str
    layer: str
    kind: str
    docs: list[str] = field(default_factory=list[str])
    allow_first_party: set[str] = field(default_factory=set[str])
    allow_third_party: set[str] = field(default_factory=set[str])
    deny_first_party: set[str] = field(default_factory=set[str])
    deny_third_party: set[str] = field(default_factory=set[str])
    enabled: bool = True
    sources: list[str] = field(default_factory=list[str])

    @property
    def effective_first_party(self) -> set[str]:
        """Allowed first-party imports after deny wins."""
        return self.allow_first_party - self.deny_first_party

    @property
    def effective_third_party(self) -> set[str]:
        """Allowed third-party imports after deny wins."""
        return self.allow_third_party - self.deny_third_party


@dataclass(frozen=True, slots=True)
class Resolution:
    """All resolved rules and the packs that produced them."""

    packs: tuple[Pack, ...]
    rules: dict[str, ResolvedRule]


@dataclass(frozen=True, slots=True)
class Project:
    """A project that consumes yaddd-agents."""

    root: Path
    pyproject_path: Path
    dependencies: dict[str, str]
    extension_paths: dict[str, str]

    @property
    def agents_dir(self) -> Path:
        """Directory with generated and hand-written agent rules."""
        return self.root / ".agents"

    @property
    def yaddd_dir(self) -> Path:
        """Directory with machine-readable yaddd configuration."""
        return self.root / ".yaddd"

    @property
    def local_rules_dir(self) -> Path:
        """Hand-written project-specific rules."""
        return self.agents_dir / "rules" / "local"

    @property
    def overrides_path(self) -> Path:
        """Hand-written local overrides."""
        return self.agents_dir / "overrides.toml"
