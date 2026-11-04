"""Command-line entry point for yaddd-agents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yaddd_agents import __version__
from yaddd_agents.discover import discover_packs, load_local_operations, load_project
from yaddd_agents.model import AgentsError, Project, Resolution
from yaddd_agents.render import check_outputs, expected_outputs, write_outputs
from yaddd_agents.resolve import explain, pack_summary, resolve


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(prog="yaddd-agents", description="Generate layered AGENTS.md rules.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--root", type=Path, default=None, help="Project root (default: nearest pyproject.toml).")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Monorepo root used to discover editable extension packs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create .agents/, .yaddd/ and sync generated files.")
    subparsers.add_parser("sync", help="Rebuild generated rules and configuration.")
    subparsers.add_parser("check", help="Fail when generated files are stale.")

    explain_parser = subparsers.add_parser("explain", help="Show where a rule comes from.")
    explain_parser.add_argument("rule", help="Rule ID, for example IMPORTS_DOMAIN.")
    explain_parser.add_argument("--json", action="store_true", help="Emit JSON.")

    list_parser = subparsers.add_parser("list", help="List active packs and rules.")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        project = load_project(args.root)
        workspace = args.workspace.resolve() if args.workspace is not None else None
        if args.command == "init":
            return _init(project, workspace)
        if args.command == "sync":
            return _sync(project, workspace)
        if args.command == "check":
            return _check(project, workspace)
        resolution = _resolve(project, workspace)
        if args.command == "explain":
            return _explain(resolution, args.rule, args.json)
        if args.command == "list":
            return _list(resolution, args.json)
    except AgentsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.error(f"unknown command: {args.command}")
    return 2


def _resolve(project: Project, workspace: Path | None) -> Resolution:
    """Discover packs and resolve every active rule."""
    packs = discover_packs(project, workspace)
    return resolve(project, packs, load_local_operations(project))


def _init(project: Project, workspace: Path | None) -> int:
    """Create directories and sync generated content."""
    project.local_rules_dir.mkdir(parents=True, exist_ok=True)
    keep = project.local_rules_dir / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")
    return _sync(project, workspace)


def _sync(project: Project, workspace: Path | None) -> int:
    """Render and write every generated file."""
    resolution = _resolve(project, workspace)
    outputs = expected_outputs(project, resolution)
    write_outputs(project, outputs)
    print(f"Synced {len(outputs)} files from {len(resolution.packs)} packs.")
    return 0


def _check(project: Project, workspace: Path | None) -> int:
    """Verify that generated files match the active packs."""
    resolution = _resolve(project, workspace)
    problems = check_outputs(project, expected_outputs(project, resolution))
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print("Run `yaddd-agents sync` to update generated files.", file=sys.stderr)
        return 1
    print(f"Agent rules are up to date ({len(resolution.rules)} rules).")
    return 0


def _explain(resolution: Resolution, rule_id: str, as_json: bool) -> int:
    """Print one resolved rule."""
    payload = explain(resolution, rule_id)
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"{payload['id']} ({payload['layer']}, {payload['kind']})")
    print(f"enabled: {'yes' if payload['enabled'] else 'no'}")
    print(f"allow first-party: {', '.join(payload['effective_first_party']) or '-'}")
    print(f"allow third-party: {', '.join(payload['effective_third_party']) or '-'}")
    print(f"deny first-party: {', '.join(payload['deny_first_party']) or '-'}")
    print(f"deny third-party: {', '.join(payload['deny_third_party']) or '-'}")
    print(f"sources: {', '.join(payload['sources']) or '-'}")
    print(f"docs: {', '.join(payload['docs']) or '-'}")
    return 0


def _list(resolution: Resolution, as_json: bool) -> int:
    """Print active packs and rules."""
    payload: dict[str, Any] = {
        "packs": pack_summary(resolution.packs),
        "rules": {rule_id: explain(resolution, rule_id) for rule_id in sorted(resolution.rules)},
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    for pack in payload["packs"]:
        print(f"{pack['name']} {pack['version']}")
    for rule_id in sorted(resolution.rules):
        print(f"  {rule_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
