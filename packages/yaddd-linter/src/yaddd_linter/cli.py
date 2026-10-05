"""CLI entry point for yaddd-linter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from yaddd_linter.checker import AggregateMutationChecker, LayerIsolationChecker, collect_aggregate_names
from yaddd_linter.rules import Violation


def _find_python_files(paths: list[Path]) -> list[Path]:
    """Collect all Python files from the given paths."""
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(path.rglob("*.py"))
    return files


def _check_paths(paths: list[Path]) -> list[Violation]:
    """Run all rules against the given paths."""
    files = _find_python_files(paths)
    aggregates = collect_aggregate_names(files)

    rules = [
        LayerIsolationChecker(),
        AggregateMutationChecker(aggregates),
    ]

    violations: list[Violation] = []
    for file in files:
        try:
            source = file.read_text(encoding="utf-8")
        except OSError:
            continue
        for rule in rules:
            violations.extend(rule.check(file, source))

    return violations


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="yaddd-linter",
        description="DDD-aware linter for yaddd projects.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to lint.",
    )
    args = parser.parse_args(argv)

    violations = _check_paths(args.paths)
    for violation in violations:
        print(violation)

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
