# NOTES — pathkit scaffold

Scaffolded a from-scratch skeleton for `pathkit`, a typed path-utility library
on top of `pathlib`, targeting Python 3.14+. Followed the
`python-314-library` skill and its `references/project-skeleton.md` template.

## What was set up and why

- **`pyproject.toml`** — single source of tool config (no `setup.cfg` /
  `mypy.ini` scatter). Key choices, all from the skill:
  - `requires-python = ">=3.14"`, `dependencies = []` (stdlib-first; the empty
    list is a deliberate product decision, kept visible with a comment).
  - Build backend **hatchling**; wheel packages `src/pathkit` so the `py.typed`
    marker ships (verified: `unzip -l dist/*.whl | grep py.typed` lists it).
  - **ruff** (`line-length = 100`, `target-version = "py314"`, rule set
    `E,F,I,B,C4,SIM,RUF,UP,PT`) — `UP` rewrites legacy syntax so the codebase
    can't drift back to "any modern Python".
  - **mypy `--strict`** *and* **pyright strict** — both are enabled at scaffold
    time; the skill treats a change as done only when `pytest`, `mypy src`,
    `pyright src`, `ruff check`, and `ruff format --check` all pass.
  - **pytest** via `pythonpath = ["src"]`, `testpaths = ["tests"]`.
  - Dev toolchain in `[dependency-groups]` (pytest / ruff / mypy / pyright),
    managed by **uv** (`.python-version` = `3.14`).
- **`src/pathkit/`** — package root `__init__.py` re-exports the public
  surface and defines `__all__` (one import line for users). Implementation
  lives in private `_core.py`, named with a leading underscore per the
  skill's private-by-convention rule.
- **`src/pathkit/py.typed`** — empty PEP 561 marker; required so downstream
  type checkers don't ignore the annotations.
- **`tests/test_core.py`** — tests call the public API the way a user would
  (`from pathkit import ensure_extension`), one behavior per test, descriptive
  names, `pytest.raises(..., match=)` for the error contract. No mocks.
- **`README.md`, `LICENSE` (MIT)** — README referenced via `dynamic` metadata
  in the template.

## Minimal working module

One public function, `ensure_extension(path, extension) -> Path`:
normalizes an extension (dot optional), returns the path unchanged if the
suffix already matches (case-insensitive), replaces a wrong suffix, and
raises `ValueError` on an empty extension. Pure stdlib (`pathlib`), no
third-party runtime deps.

## Verification (all green in /tmp/pathkit)

```
ruff check .            # All checks passed
ruff format --check .   # 4 files already formatted
mypy src                # Success: no issues found in 2 source files
pyright src             # 0 errors, 0 warnings
pytest                  # 6 passed
uv build                # wheel contains pathkit/py.typed
```

## Notes

- The project tree was copied from `/tmp/pathkit` excluding build/venv
  artifacts (`.venv`, `dist`, caches); `uv.lock` and `.python-version` are
  included so the toolchain pins travel with the skeleton.
