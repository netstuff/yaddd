# NOTES: settings module design decisions

## Files

- `settings_config.py` — the module source (would live at `src/yaddd/settings_config.py`; the existing `src_old/yaddd/settings/` was pydantic-based and is superseded by this stdlib-only version).
- `test_settings_config.py` — pytest suite (would live at `tests/unit/test_settings_config.py`; repo pytest config already sets `pythonpath = ["src"]`, so `from yaddd.settings_config import ...` resolves).
- `package_init_example.py` — shows how to re-export the public API from `src/yaddd/__init__.py` with an explicit `__all__`.

## Design

- **Stdlib only.** No pydantic / pydantic-settings, keeping `dependencies = []` in pyproject.toml. Only `os`, `typing`, `collections.abc` are used.
- **Declaration via class annotations + `Field()`**, mirroring the ergonomic style of pydantic-settings so migration is easy. A class attribute without `Field()` also works as a plain default (`plain_default = "from-class"`).
- **`BaseSettings.load(env=None)`** is an explicit factory (not implicit on instantiation) so tests can inject a mapping. `env=None` reads `os.environ`.
- **Type coercion** driven by annotations: `str`, `int`, `float`, `bool` (accepts `1/0, true/false, yes/no, on/off`), `list[X]`/`tuple/set/frozenset[X]` parsed from comma-separated values, and `X | None` (empty env value falls back to the default/`None`).
- **`env_prefix` ClassVar** on the class; per-field override via `Field(env="NAME")`. Otherwise the env name is `PREFIX + FIELD_NAME.upper()`.
- **Immutability:** instances are frozen (`__setattr__` raises); values live in a `_values` dict resolved once at `load()` time.
- **Inheritance:** a metaclass collects fields across the MRO; subclass fields are merged with parent defaults.
- **Errors:** `SettingsError` base with `MissingEnvVarError` (carries the env var name) and `InvalidValueError` (carries name, raw value, target type) — exceptions carry structured attributes so callers don't need to parse messages.

## Notable choices / caveats

- Class-level `Field(...)` declarations are **deleted from the class dict** by the metaclass after collection — otherwise the class attribute would shadow the instance value (`__getattr__` is only called when normal lookup fails). This was an actual bug caught by the first test run.
- An empty env value for a required non-sequence field raises `InvalidValueError` rather than silently passing `""` through; empty value for an optional field means `None`/default. Adjust to taste.
- No `.env` file parsing (kept dependency-free; repo already relies on pytest-env for tests) and no nested-settings support — deliberately out of scope for a first version.
- Style follows repo conventions: double quotes, line-length 120, module docstrings, ruff lint rules (`__init__.py` gets `F401` per-file-ignore so re-exports don't trip lint).

## Verification

All 16 tests pass (run with `uv run --with pytest --no-project python -m pytest`, Python 3.13/3.14).
