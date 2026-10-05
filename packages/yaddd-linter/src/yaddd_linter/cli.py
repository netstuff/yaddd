"""CLI entry point for yaddd-linter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yaddd_linter import __version__
from yaddd_linter.checker import AggregateMutationChecker, LayerIsolationChecker, collect_aggregate_names
from yaddd_linter.config import Config, load_config
from yaddd_linter.rules import ALL_CODES, Violation


class _CliError(Exception):
    """An error that should be reported to the user with exit code 2."""


class _JsonEncoder(json.JSONEncoder):
    """Encode pathlib objects as strings for JSON output."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Path):
            return str(o)
        return super().default(o)


def _parse_codes(value: str | None) -> frozenset[str] | None:
    """Parse a comma-separated list of rule codes."""
    if value is None:
        return None
    return frozenset(code.strip() for code in value.split(",") if code.strip())


def _resolve_codes(
    cli_select: frozenset[str] | None,
    cli_ignore: frozenset[str] | None,
    config: Config,
) -> frozenset[str]:
    """Combine CLI flags and config into the final enabled code set."""
    select = cli_select if cli_select is not None else config.select
    ignore = cli_ignore if cli_ignore is not None else config.ignore
    unknown = (select | ignore) - ALL_CODES
    if unknown:
        raise ValueError(f"Unknown yaddd-linter rule codes: {sorted(unknown)}")
    if select:
        return frozenset(code for code in select if code not in ignore)
    return ALL_CODES - ignore


def _load_sources(
    paths: list[Path],
    stdin_filename: Path | None,
) -> list[tuple[Path, str]]:
    """Return (path, source) pairs for all requested inputs."""
    sources: list[tuple[Path, str]] = []
    for path in paths:
        if path.name == "-":
            filename = stdin_filename or Path("<stdin>")
            try:
                sources.append((filename, sys.stdin.read()))
            except OSError as exc:
                raise _CliError(f"Cannot read stdin: {exc}") from exc
            continue

        if path.is_file() and path.suffix == ".py":
            try:
                sources.append((path, path.read_text(encoding="utf-8")))
            except OSError as exc:
                raise _CliError(f"Cannot read {path}: {exc}") from exc
        elif path.is_dir():
            for file in path.rglob("*.py"):
                try:
                    sources.append((file, file.read_text(encoding="utf-8")))
                except OSError as exc:
                    raise _CliError(f"Cannot read {file}: {exc}") from exc
    return sources


def _check_sources(
    sources: list[tuple[Path, str]],
    enabled_codes: frozenset[str],
) -> list[Violation]:
    """Run all rules against the given sources and filter by enabled codes."""
    files = [path for path, _ in sources]
    aggregates = collect_aggregate_names(files)

    rules = [
        LayerIsolationChecker(),
        AggregateMutationChecker(aggregates),
    ]

    violations: list[Violation] = []
    for path, source in sources:
        for rule in rules:
            for violation in rule.check(path, source):
                if violation.code in enabled_codes:
                    violations.append(violation)
    return violations


def _print_text(violations: list[Violation]) -> None:
    """Print violations in ruff-compatible text format."""
    for violation in violations:
        print(violation)


def _print_json(violations: list[Violation]) -> None:
    """Print violations as a JSON array."""
    payload = [
        {
            "path": violation.path,
            "line": violation.line,
            "col": violation.col,
            "code": violation.code,
            "message": violation.message,
        }
        for violation in violations
    ]
    print(json.dumps(payload, cls=_JsonEncoder, indent=2))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="yaddd-linter",
        description="DDD-aware linter for yaddd projects.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to lint. Use '-' for stdin.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--stdin-filename",
        type=Path,
        default=None,
        help="Filename to use when reading from stdin (affects layer detection).",
    )
    parser.add_argument(
        "--select",
        type=str,
        default=None,
        help="Comma-separated list of rule codes to enable.",
    )
    parser.add_argument(
        "--ignore",
        type=str,
        default=None,
        help="Comma-separated list of rule codes to disable.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to pyproject.toml containing [tool.yaddd-linter].",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)

    if not args.paths:
        parser.error("the following arguments are required: paths")

    try:
        config = load_config(args.config)
        cli_select = _parse_codes(args.select)
        cli_ignore = _parse_codes(args.ignore)
        enabled_codes = _resolve_codes(cli_select, cli_ignore, config)
        sources = _load_sources(args.paths, args.stdin_filename)
        violations = _check_sources(sources, enabled_codes)
    except _CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        _print_json(violations)
    else:
        _print_text(violations)

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
