# NOTES — pathkit scaffold (without_skill run)

## What was built
A from-scratch skeleton for `pathkit` (path utilities on top of `pathlib`, Python 3.14+):

```
pyproject.toml          # PEP 621 metadata + all tool config in one place
README.md
.gitignore
src/pathkit/__init__.py # re-exports ensure_extension
src/pathkit/_core.py    # ensure_extension(path, extension) -> Path
src/pathkit/py.typed     # PEP 561 typed marker (empty file)
tests/test_core.py       # 5 tests covering the function
```

## Setup decisions

- **Build backend: hatchling.** Lightweight, PEP 621-native, is the default in
  modern uv workflows. Wheel layout configured via
  `[tool.hatch.build.targets.wheel] packages = ["src/pathkit"]`.
- **src layout** — prevents accidental imports of the uninstalled package and
  forces the test suite to exercise the installed/importable path configured
  via `pythonpath = ["src"]` in pytest options.
- **`requires-python = ">=3.14"`**, `target-version = "py314"` (ruff),
  `python_version = "3.14"` (mypy), `pythonVersion = "3.14"` (pyright) — all
  toolchains pinned to the same floor.
- **Dependencies: none.** Core deliberately ships zero runtime deps;
  integrations would go into optional-dependencies later, never in core.
- **Dev dependencies** live in `[dependency-groups] dev` (PEP 735, supported by
  uv and recent pip): pytest, ruff, mypy, pyright — so lint/typecheck/test
  tooling versions are locked together.
- **Ruff**: line-length 100, rule set E/F/I/B/C4/SIM/RUF/UP/PT. UP (pyupgrade)
  keyed to `py314` auto-enforces modern syntax; PT enforces pytest style.
- **Type checking: both mypy and pyright, both strict.** mypy via
  `strict = true` + `warn_unreachable`; pyright via
  `typeCheckingMode = "strict"`. Running both catches a wider class of
  inference disagreements than either alone.
- **py.typed**: empty marker file inside the package, picked up by hatchling
  automatically (verified present in the built wheel).
- **pytest**: `pythonpath = ["src"]` (no editable install needed to test),
  `testpaths = ["tests"]`, concise `-ra -q` output.

## Verification (all run under the real Python 3.14.6)
- `pytest` — 5 passed
- `ruff check .` — all checks passed
- `mypy` (strict) — no issues in 2 source files
- `pyright` (strict) — 0 errors, 0 warnings
- `hatchling build -t wheel` — wheel contains `pathkit/py.typed`

## Environment note
`/tmp/pathkit` was being written concurrently by another agent process during
this run, so the project was first assembled in a private staging dir
(`/tmp/pathkit-agent-build`), verified there, and only then copied into
`/tmp/pathkit` and into this outputs directory. The copied tree is identical
to the verified one.
