---
name: python-314-library
description: >-
  Standards for designing, writing, scaffolding, and reviewing Python libraries
  targeting Python 3.14+. Use this skill whenever the user writes or edits
  library code under src/, scaffolds a new package or module, designs a public
  API, adds typing (Protocol, Generic, TypeVar), writes tests, touches
  pyproject.toml, or asks for a code review — even if they don't explicitly ask
  for "best practices". Also use it when the user mentions dependency choices,
  exception design, __all__ / py.typed, or strict type checking for this repo.
  The repo follows stdlib-first dependency policy, DRY/KISS, strict typing
  checked by BOTH mypy --strict and pyright, and pytest for tests.
---

# Python 3.14+ Library Development Standards

These standards exist so the library stays small, typed, and pleasant to use.
Every rule below traces back to one of three commitments: **minimal
dependencies**, **strict static typing**, **simple public interfaces**. When a
rule and a shortcut conflict, the rule wins — a user of this library reads the
public API, not the implementation.

## 1. Dependency policy: stdlib first, always

The library's `dependencies = []` is a feature. Adding a third-party package
is a design decision that outlives the code that needed it.

- Before importing anything outside stdlib, check the Python 3.14 stdlib
  surface: `itertools`, `functools`, `collections`, `dataclasses`, `enum`,
  `typing`, `contextlib`, `pathlib`, `compression.zstd`, `concurrent.interpreters`.
  The 3.14 stdlib is larger than muscle memory suggests.
- A dependency is justified only when it does something the stdlib cannot do
  **well** (e.g. `pydantic` for validation ergonomics, `sqlalchemy` for ORM),
  not merely faster or with a nicer name.
- Optional integrations (like the existing `sqlalchemy` / `pydantic` extras)
  go in `[project.optional-dependencies]`, never in core `dependencies`.
  Import them lazily inside the integration module so core never pays the cost.
- Never add a dependency for a single small function. Ten lines of stdlib code
  beat a transitive dependency tree.

## 2. Strict typing is non-negotiable

Every public symbol must be fully annotated. Untyped code defeats the point of
a typed library: your users' checkers will see `Any` where they expected help.

- Run and pass **both** `mypy --strict` and `pyright` (basic or strict).
  Configs live in `pyproject.toml` (see `references/project-skeleton.md`).
  A change is not done until all three of these pass: `pytest`, `mypy src`,
  `pyright src` — plus `ruff check` and `ruff format`.
- Ship `py.typed` in the package root and include it in the build
  (`[tool.hatch.build.targets.wheel] packages = [...]` with the marker file
  present). Without it, downstream type checkers ignore every annotation.
- No `# type: ignore` without a comment naming the exact false positive and
  why the checker is wrong. If both checkers complain, the code is usually
  wrong, not the checkers.
- Prefer structural typing with `Protocol` over ABCs for interfaces users
  implement. Use `abc.ABC` only when you need real inheritance (shared state
  or `super()` behavior).
- Use modern generics: PEP 696 type parameter defaults
  (`class Repository[T, TId = UUID]`), `ParamSpec` for decorators, `Self` for
  fluent methods, `TypeVarTuple` where genuinely variadic.
- Use `@overload` when one function has meaningfully different signatures per
  input type — overloads are documentation the checker enforces.
- `@runtime_checkable` Protocols are for `isinstance` narrowing only; they do
  not check method signatures at runtime. Don't let that surprise users.

## 3. Python 3.14 specifics (not "any modern Python")

Target is `requires-python = ">=3.14"` — write 3.14 code, don't write
3.10-compatible code out of habit.

- **PEP 649/749 — deferred annotations are now default.** `cls.__annotations__`
  holds strings/lazily-computed values, not types. Never read `__annotations__`
  directly; use `inspect.get_annotations(cls)` or `typing.get_type_hints()`.
  Anything that introspects annotations at class-creation time (validators,
  registries, serializers) must go through these functions.
- **PEP 750 — t-strings (`t"..."`)**: when producing string templates users
  will fill in (SQL snippets, message templates, path patterns), t-strings are
  the safe choice — they don't commit to the interpolation policy. For plain
  internal messages, plain f-strings are fine.
- **`warnings.deprecated`** (PEP 702, stdlib since 3.13): the only sanctioned
  way to deprecate. `@warnings.deprecated("use X; removed in 1.0")` on the old
  symbol — silent behavior changes are forbidden.
- **Free-threaded builds (no-GIL) are in the wild.** Avoid module-level mutable
  caches and global registries; prefer passing state explicitly. If a cache is
  truly needed, keep it an implementation detail behind a function and document
  thread-safety honestly.
- No `typing_extensions`, no `six`-style compatibility shims. If it's in
  stdlib 3.14, import it from stdlib.

## 4. Public API design: small surface, obvious names

Users judge the library by the top of its import list.

- The package `__init__.py` re-exports the intended public surface and defines
  `__all__`. Users should need one import line for 95% of use cases.
- Every module that is not the package root also declares `__all__` for its
  own re-exports. Anything not in `__all__` is private by convention (and
  named with a leading `_` at the definition site).
- New public names follow the existing naming vocabulary of the library; don't
  introduce a synonym for a concept that already has a name.
- Prefer keyword-only arguments for functions with more than one parameter or
  any boolean parameter (`def connect(*, timeout: float, retry: bool) -> ...`).
  Booleans as positional arguments are a readability trap.
- Dataclasses and lightweight value objects: use `slots=True`
  (`@dataclass(slots=True)` or `class P(slots=True)` in 3.14). It is nearly
  free and prevents a whole class of attribute-typo bugs.
- Exceptions are part of the API. Define a small exception hierarchy rooted at
  a library-specific base (e.g. `class YadddError(Exception)`), raise the most
  specific subclass, chain with `raise ... from ...`, and add context with
  `exc.add_note(...)` (PEP 678) instead of string-munging error messages.

## 5. Code principles applied concretely

DRY and KISS are outcomes, not licenses to build machinery.

- **DRY**: the moment the same non-trivial logic appears twice, extract it.
  But do not extract a one-line expression that appears twice — two identical
  lines are cheaper than a wrong abstraction.
- **KISS**: the simplest implementation that passes tests and type checks wins.
  If you are adding a class hierarchy to avoid one `if`, you have failed KISS.
  Composition of plain functions beats deep inheritance.
- **Readability over cleverness**: no metaclasses unless the domain genuinely
  requires them; no `getattr` string dispatch when a `dict` of callables works;
  no decorators that rewrite function signatures (breaks typing and greppability).
- **Performance**: correct first, fast only when measured. `__slots__`, lazy
  imports of heavy optional deps, and avoiding O(n²) loops in obvious places
  are the only optimizations allowed without a profiler result or an explicit
  user request.

## 6. Tests

- pytest is the test runner (already in `dependency-groups.dev`). It is the
  sanctioned exception to stdlib-first: the fixture/parametrize ergonomics
  justify it.
- Test the public API as a user would call it — not private methods. A test
  that reaches into `_private` names is a smell that the public surface is
  incomplete.
- One behavior per test, descriptive test names (`test_registry_rejects_duplicate_key`,
  not `test_2`).
- Use `pytest.raises` with `match=` to assert both the exception type and the
  message contract.
- No mocks of the library's own internals; fake implementations of library
  Protocols are fine and preferred.
- Coverage is a signal, not a goal: untested public API is the bug to fix.

## 7. Working in this repo

- Package manager: **uv**; build backend: **hatchling**. Use
  `uv sync --group all` to get the full toolchain.
- Run before considering any change complete:
  `ruff check . && ruff format --check . && mypy src && pyright src && pytest`
- Optional integrations (pydantic, sqlalchemy) must keep core dependency-free:
  their imports live inside the integration module, never at package import
  time. See how `src/yaddd/domain/value_object/sqlalchemy/` isolates it.
- New module layout: public surface up top, private helpers at the bottom,
  imports sorted by ruff/isort rules.

## 8. Scaffolding and review

- When the user asks to create a new library, package, or module from scratch,
  read `references/project-skeleton.md` for the pyproject/tooling template
  instead of inventing config.
- When the user asks for a review or "check this before merge", walk the
  checklist in `references/review-checklist.md` — it encodes everything above
  as pass/fail items.
