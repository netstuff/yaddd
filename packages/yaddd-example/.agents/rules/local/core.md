# Project-specific core rules

This repository is a starting point for a web application, not a library. One
illustrative slice (`orders`) is implemented end to end: copy the pattern,
delete the example, keep the architecture.

## Commands

```bash
uv sync --all-groups   # environment
make agents            # regenerate .agents/rules/base and .agents/rules/extensions
make check             # agents check, ruff format --check, ruff check, yaddd-linter, ty, pyright, pytest
make test              # pytest only
make fmt               # ruff format + autofixes
make lock              # re-resolve uv.lock after changing dependencies
```

`yaddd-linter` is not on PyPI yet: `uv tool install ./packages/yaddd-linter`,
or `uv pip install ../yaddd-linter` from this directory in the monorepo.

## Verification

`make check` is the single gate: generated agent rules, formatting, lint,
architecture, strict types and tests. Run it before calling work done.
