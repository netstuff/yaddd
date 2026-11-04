# Tooling and typing: project specifics

Additive to the base tooling rules. Never relaxes core rules; on conflict, core
wins.

## Gates

`make check` runs every gate; `make lint` is ruff plus `yaddd-linter`, and
`make types` is ty plus pyright. `yaddd-linter` rules are selected explicitly
in `[tool.yaddd-linter]` in `pyproject.toml`.

## Style

- `ruff format` is the formatter of record; line length 120.
- PEP 695 generics (`class Container[T]`), `X | None` unions, `type` aliases.

## Typing

`ty` and `pyright` run in strict mode over `app` and `tests`.

`yaddd` builds framework classes at runtime, so neither checker sees the
synthesized keyword-only `__init__` of aggregates, commands, events and DTOs.
That `unknown-argument` / `reportCallIssue` noise is suppressed centrally in
`pyproject.toml`, not with inline pragmas.
