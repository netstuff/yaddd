# Pre-merge review checklist

Walk this list for any change to library code, and report findings grouped by
section. Each item is pass/fail — "pass" means either satisfied or explicitly
justified in the change description.

## Dependencies

- [ ] No new third-party dependency in core `dependencies`. New ones, if truly
      necessary, are in `[project.optional-dependencies]` and imported lazily
      inside the integration module.
- [ ] No stdlib-capable problem solved by a dependency (checked against the
      3.14 stdlib surface).
- [ ] No `typing_extensions`, no backport shims (target is 3.14+).

## Typing

- [ ] `mypy --strict` passes.
- [ ] `pyright` (strict) passes.
- [ ] Every `# type: ignore` has an inline comment naming the false positive.
- [ ] `py.typed` present and included in the built wheel.
- [ ] User-implemented interfaces are `Protocol`s (structural), not ABCs,
      unless inheritance semantics are genuinely required.
- [ ] Generics use PEP 696 defaults where a type parameter has an obvious
      default; `@overload` used where signatures diverge by input type;
      `ParamSpec` on decorators; `Self` on fluent methods.
- [ ] Annotations are read via `inspect.get_annotations()` /
      `typing.get_type_hints()` where runtime introspection happens — no raw
      `__annotations__` access (PEP 649 default in 3.14).

## Public API

- [ ] New public symbols are exported (or deliberately not) from the package
      root; `__all__` updated in the module and the package `__init__`.
- [ ] No accidental public name: everything else starts with `_` or stays
      module-private.
- [ ] Multi-arg / boolean-arg functions use keyword-only parameters.
- [ ] Value types use `slots=True`.
- [ ] The new API fits the library's existing naming vocabulary — no synonym
      for an existing concept.
- [ ] Exceptions: most specific library subclass raised, `raise ... from ...`
      chains preserved, context added via `add_note()`, never by string
      concatenation into the message.

## Deprecation & compatibility

- [ ] Nothing was silently renamed/removed: old symbols carry
      `@warnings.deprecated` with a migration message.
- [ ] No module-level mutable global state added without an explicit note on
      free-threaded (no-GIL) safety.

## Code quality

- [ ] Repeated non-trivial logic extracted (DRY) — but no abstraction for
      one-liners repeated twice.
- [ ] No class hierarchy where a function or dict of functions suffices (KISS).
- [ ] No metaclasses, no signature-rewriting decorators, no `getattr` string
      dispatch — unless the change message explains why the domain requires it.
- [ ] No optimization without a measurement or explicit request.

## Tests

- [ ] New public behavior covered by pytest tests that call it the way a user
      would — no tests reaching into `_private` names.
- [ ] `pytest.raises(..., match=...)` asserts the message contract for
      exceptions.
- [ ] Fakes implement the library's Protocols instead of `unittest.mock`
      patching internals.
- [ ] Optional-dependency integrations have an import-skip guard
      (`pytest.importorskip`) so the core suite runs without extras.

## Toolchain (run before merge)

- [ ] `ruff check . && ruff format --check .` — clean
- [ ] `mypy src` — clean
- [ ] `pyright src` — clean
- [ ] `pytest` — green
