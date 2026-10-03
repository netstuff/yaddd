# Project skeleton: pyproject.toml for a new Python 3.14+ library

Copy this template when scaffolding a new library, then trim optional parts.
All tool config lives in one file — do not scatter `setup.cfg`, `.isort.cfg`,
`mypy.ini`, etc.

```toml
[project]
name = "my-lib"
description = "..."
requires-python = ">=3.14"
dependencies = []  # stays empty until a dependency is PROVEN necessary
version = "0.1.0"
dynamic = ["readme"]
license = "MIT"
license-files = ["LICENSE"]
classifiers = [
    "Programming Language :: Python :: 3.14",
    "Typing :: Typed",  # signals py.typed to indexers
]

[project.optional-dependencies]
# Add integrations here, never in core. Example:
# sqlalchemy = ["sqlalchemy>=2.0"]

[dependency-groups]
dev = ["pytest>=8"]
linting = ["ruff>=0.8"]
typechecking = ["mypy>=1.14", "pyright>=1.1.392"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/my_lib"]

# ---------- linting & formatting ----------

[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = [
    "E", "F", "I",   # pycodestyle, pyflakes, isort
    "B",             # bugbear
    "C4",            # comprehensions
    "SIM",           # simplify
    "RUF",           # ruff-specific (catches 3.14-isms)
    "UP",            # pyupgrade — enforces modern syntax for target-version
    "PT",            # pytest style
]
ignore = [
    "D",             # docstring enforcement is a project policy decision
]

# ---------- type checking: BOTH, strict ----------

[tool.mypy]
python_version = "3.14"
strict = true
mypy_path = "src"
packages = ["my_lib"]

[tool.pyright]
pythonVersion = "3.14"
typeCheckingMode = "strict"

# ---------- tests ----------

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-v"
```

## Required files alongside pyproject.toml

```
pyproject.toml
src/my_lib/__init__.py     # public surface + __all__
src/my_lib/py.typed        # EMPTY file — PEP 561 marker, required for downstream checkers
src/my_lib/...
tests/...
README.md
LICENSE
.python-version            # content: "3.14" (for uv)
```

## Rules baked into this template — and why

- **`strict = true` + pyright strict in the same file.** The library must pass
  both. Enabling them at scaffold time is nearly free; retrofitting strict mode
  onto a lax codebase is days of pain.
- **`target-version = "py314"` + `UP` rules.** Ruff will then auto-flag
  legacy-compatible syntax (old `typing.Dict`, `Optional[x]`, class-based
  `super()` calls) and rewrite it to 3.14 idiom. This keeps the codebase from
  drifting back to "any modern Python".
- **`dependencies = []` with a comment.** The empty list is a deliberate
  product decision — make it visible so no one fills it casually.
- **`py.typed` must be committed**, and since hatchling includes all package
  files by default for the wheel it just needs to exist in `src/my_lib/`.
  Verify with `unzip -l dist/*.whl | grep py.typed` after build.
- **uv as the package manager** (`uv sync --group dev --group linting --group typechecking`
  installs everything). One `uv.lock`, one source of truth.

## Sanity commands after scaffolding

```bash
uv sync --all-groups
ruff check . && ruff format --check .
mypy src
pyright src
pytest
uv build && unzip -l dist/*.whl | grep py.typed   # must list the marker
```
