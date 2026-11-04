"""Copy the application template out of the monorepo into a standalone project."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = REPO_ROOT / "packages" / "yaddd-example"
PLACEHOLDER = "yaddd-example"
IGNORE = shutil.ignore_patterns(
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".ty",
    "dist",
    "build",
    "*.egg-info",
    ".DS_Store",
    "uv.lock",
)
_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
_SOURCES = re.compile(r"(?ms)^\[tool\.uv\.sources\]\n(?:.*\n)*?(?=^\[|\Z)")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="standalone",
        description="Copy packages/yaddd-example into a standalone project.",
    )
    parser.add_argument("name", help="Project name, for example acme-orders.")
    parser.add_argument("--output", type=Path, default=None, help="Destination directory (default: dist/<name>).")
    parser.add_argument("--force", action="store_true", help="Replace the destination when it already exists.")
    return parser


def _strip_path_sources(text: str) -> str:
    """Remove the monorepo-only ``[tool.uv.sources]`` table."""
    stripped = _SOURCES.sub("", text)
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    return stripped.rstrip() + "\n"


def _rewrite(path: Path, name: str) -> None:
    """Replace the template name and drop monorepo path sources."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    updated = text.replace(PLACEHOLDER, name)
    if path.name == "pyproject.toml":
        updated = _strip_path_sources(updated)
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def _copy(name: str, output: Path, force: bool) -> None:
    if output.exists():
        if not force:
            raise SystemExit(f"destination already exists: {output} (use --force)")
        shutil.rmtree(output)
    shutil.copytree(TEMPLATE_ROOT, output, ignore=IGNORE)
    for path in sorted(output.rglob("*")):
        if path.is_file():
            _rewrite(path, name)


def main(argv: list[str] | None = None) -> int:
    """Copy the template and rewrite its project identity."""
    args = _parser().parse_args(argv)
    name = args.name.strip()
    if _NAME.fullmatch(name) is None:
        print("error: name must match ^[a-z][a-z0-9-]*$", file=sys.stderr)
        return 2
    output = (args.output or REPO_ROOT / "dist" / name).resolve()
    if output == TEMPLATE_ROOT or TEMPLATE_ROOT in output.parents:
        print("error: destination must be outside packages/yaddd-example", file=sys.stderr)
        return 2
    _copy(name, output, args.force)
    print(f"Created {output}")
    print("Next: cd into it, run `uv lock`, then `make install` and `make check`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
