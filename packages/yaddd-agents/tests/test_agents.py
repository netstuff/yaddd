"""Tests for yaddd-agents discovery, resolution and rendering."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from yaddd_agents.cli import main
from yaddd_agents.discover import load_project
from yaddd_agents.model import MANAGED_BEGIN, MANAGED_END
from yaddd_agents.resolve import _satisfies


def _write_project(tmp_path: Path, extensions: dict[str, str] | None = None) -> Path:
    """Create a minimal project with optional explicit extension packs."""
    pyproject = tmp_path / "pyproject.toml"
    lines = [
        "[project]",
        'name = "demo"',
        'version = "0.1.0"',
        'dependencies = ["yaddd>=0.4"]',
        "",
    ]
    if extensions:
        lines.extend(["[tool.yaddd.agents.extensions]"])
        lines.extend(f'{name} = "{path}"' for name, path in extensions.items())
        lines.append("")
    pyproject.write_text("\n".join(lines), encoding="utf-8")
    return tmp_path


def _write_pack(root: Path, name: str, manifest: str, docs: dict[str, str]) -> Path:
    """Create an extension pack and return its manifest path."""
    pack_dir = root / "ext" / name
    (pack_dir / "rules").mkdir(parents=True, exist_ok=True)
    (pack_dir / "manifest.toml").write_text(textwrap.dedent(manifest), encoding="utf-8")
    for filename, content in docs.items():
        (pack_dir / "rules" / filename).write_text(textwrap.dedent(content), encoding="utf-8")
    return pack_dir / "manifest.toml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_sync_creates_generated_files(tmp_path: Path) -> None:
    manifest = _write_pack(
        tmp_path,
        "demo",
        """
        schema = 1
        name = "demo"
        version = "0.1.0"

        [[relaxes]]
        rule = "IMPORTS_DOMAIN"
        allow_add = ["pydantic"]
        reason = "The demo pack sanctions pydantic in the domain."

        [rules.DEMO_GUIDANCE]
        layer = "domain"
        kind = "guidance"
        doc = "rules/domain.md"
        """,
        {"domain.md": "# Demo domain\n\nUse pydantic.\n"},
    )
    _write_project(tmp_path, {"demo": str(manifest.relative_to(tmp_path))})

    assert main(["--root", str(tmp_path), "sync"]) == 0

    agents = _read(tmp_path / "AGENTS.md")
    assert MANAGED_BEGIN in agents
    assert MANAGED_END in agents
    assert "Core rules" in agents
    assert ".agents/rules/base/domain.md" in agents
    assert ".agents/rules/extensions/demo/domain.md" in agents

    layers = json.loads(_read(tmp_path / ".yaddd" / "layers.json"))
    assert layers["layers"]["domain"]["third_party"] == ["pydantic"]
    assert (tmp_path / ".agents" / "manifest.lock.json").is_file()
    assert (tmp_path / ".agents" / "rules" / "base" / "domain.md").is_file()
    assert (tmp_path / ".agents" / "rules" / "extensions" / "demo" / "domain.md").is_file()


def test_check_detects_drift_and_sync_restores(tmp_path: Path, capsys) -> None:
    _write_project(tmp_path)
    assert main(["--root", str(tmp_path), "sync"]) == 0

    agents = tmp_path / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "\ndrift\n", encoding="utf-8")

    assert main(["--root", str(tmp_path), "check"]) == 1
    assert "stale:" in capsys.readouterr().err

    assert main(["--root", str(tmp_path), "sync"]) == 0
    assert main(["--root", str(tmp_path), "check"]) == 0


def test_local_rules_are_preserved_and_routed(tmp_path: Path) -> None:
    _write_project(tmp_path)
    local = tmp_path / ".agents" / "rules" / "local"
    local.mkdir(parents=True)
    (local / "domain.md").write_text("# Local domain\n", encoding="utf-8")

    assert main(["--root", str(tmp_path), "sync"]) == 0
    assert (local / "domain.md").read_text(encoding="utf-8") == "# Local domain\n"
    assert ".agents/rules/local/domain.md" in _read(tmp_path / "AGENTS.md")


def test_restrict_wins_over_relax(tmp_path: Path) -> None:
    manifest = _write_pack(
        tmp_path,
        "demo",
        """
        schema = 1
        name = "demo"
        version = "0.1.0"

        [[relaxes]]
        rule = "IMPORTS_DOMAIN"
        allow_add = ["pydantic"]
        reason = "Sanction pydantic."

        [rules.DEMO_GUIDANCE]
        layer = "domain"
        doc = "rules/domain.md"
        """,
        {"domain.md": "# Demo\n"},
    )
    _write_project(tmp_path, {"demo": str(manifest.relative_to(tmp_path))})
    overrides = tmp_path / ".agents" / "overrides.toml"
    overrides.parent.mkdir(parents=True)
    overrides.write_text(
        textwrap.dedent(
            """
            [[restricts]]
            rule = "IMPORTS_DOMAIN"
            deny_add = ["pydantic"]
            reason = "This project forbids pydantic in the domain."
            """
        ),
        encoding="utf-8",
    )

    assert main(["--root", str(tmp_path), "sync"]) == 0
    layers = json.loads(_read(tmp_path / ".yaddd" / "layers.json"))
    assert layers["layers"]["domain"]["third_party"] == []


def test_explain_shows_sources(tmp_path: Path, capsys) -> None:
    manifest = _write_pack(
        tmp_path,
        "demo",
        """
        schema = 1
        name = "demo"
        version = "0.1.0"

        [[relaxes]]
        rule = "IMPORTS_DOMAIN"
        allow_add = ["pydantic"]
        reason = "Sanction pydantic."

        [rules.DEMO_GUIDANCE]
        layer = "domain"
        doc = "rules/domain.md"
        """,
        {"domain.md": "# Demo\n"},
    )
    _write_project(tmp_path, {"demo": str(manifest.relative_to(tmp_path))})

    assert main(["--root", str(tmp_path), "explain", "IMPORTS_DOMAIN"]) == 0
    output = capsys.readouterr().out
    assert "IMPORTS_DOMAIN" in output
    assert "base" in output
    assert "demo:relax" in output


def test_stale_extension_files_are_removed(tmp_path: Path) -> None:
    _write_project(tmp_path)
    stale = tmp_path / ".agents" / "rules" / "extensions" / "old" / "domain.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("# Old\n", encoding="utf-8")

    assert main(["--root", str(tmp_path), "sync"]) == 0
    assert not stale.exists()


def test_manifest_operation_requires_reason(tmp_path: Path) -> None:
    manifest = _write_pack(
        tmp_path,
        "demo",
        """
        schema = 1
        name = "demo"
        version = "0.1.0"

        [[relaxes]]
        rule = "IMPORTS_DOMAIN"
        allow_add = ["pydantic"]
        """,
        {"domain.md": "# Demo\n"},
    )
    _write_project(tmp_path, {"demo": str(manifest.relative_to(tmp_path))})

    assert main(["--root", str(tmp_path), "sync"]) == 2


def test_version_specifier_subset() -> None:
    assert _satisfies("0.1.1", ">=0.1")
    assert _satisfies("1.4.5", "~=1.4")
    assert not _satisfies("1.3.9", ">=1.4")
    assert not _satisfies("2.0", "<2.0")


def test_project_dependencies_include_dev_groups(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """
            [project]
            name = "demo"
            version = "0.1.0"
            dependencies = ["yaddd>=0.4"]

            [dependency-groups]
            dev = ["yaddd-pydantic>=0.1", { include-group = "linting" }]
            linting = ["yaddd-sqlalchemy>=0.1"]
            """
        ),
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    assert "yaddd-pydantic" in project.dependencies
    assert "yaddd-sqlalchemy" in project.dependencies
