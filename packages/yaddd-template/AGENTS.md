# Rules for AI agents and humans working in this repository.

## What this is

A starting point for a web application, not a library. It contains one
illustrative business slice (`orders`) implemented end to end. Treat the
example as a pattern to copy and delete; treat the architecture as a rule.

## Commands

```bash
uv sync --all-groups   # environment
make check             # ruff format --check, ruff check, yaddd-linter, ty, pyright, pytest
make test              # pytest only
make fmt               # ruff format + autofixes
make lock              # re-resolve uv.lock after changing dependencies
```

`yaddd-linter` is not on PyPI yet. Install it once from a checkout of the
yaddd repository: `uv tool install ./packages/yaddd-linter`, or, from this
directory inside the monorepo, `uv pip install ../../yaddd-linter`.

## Architecture rules

Dependencies point inwards. `domain` knows nothing; `application` depends on
`domain`; `infrastructure` implements ports declared by `domain` and
`application`; `presentation` talks to `application` through injected ports.

- **`domain/`** — aggregates, entities, value objects, domain events, business
  rules, repository interfaces. Imports: `yaddd`, stdlib, `pydantic` and
  `yaddd_pydantic` — `PydanticVO` is the sanctioned base for value objects that
  double as request and column types, with constraints declared through
  `pydantic.Field`. No FastAPI, no SQLAlchemy, no other third-party package.
- **Aggregates live in `domain/<slice>/aggregates/`**, one aggregate per module.
  The module name matches the aggregate name in snake_case, e.g.
  `aggregates/order.py` for `Order`.
- **Business-rule names are imperative.** A rule describes the constraint that
  must hold, e.g. `TotalMustBePositive` or `OrderMustBePlaced`, never
  `PositiveTotal` or `PlacedOnly`. A rule is a small object with
  `is_satisfied_by`, a `message`, and `&`/`|` composition — put invariants in
  `INVARIANTS` and behavioural rules on the aggregate as `ClassVar` rule
  instances.
- **`application/`** — commands, handlers (`@command_handler`), DTOs, mappers,
  the unit-of-work port, projections, and the health vocabulary. Framework
  free: it may import `yaddd`, never FastAPI or FastStream.
- **`infrastructure/`** — SQLAlchemy Core tables and adapters, Redis broker,
  publisher, probes, settings, logging. Implements ports; never invents new
  vocabulary for the domain.
- **`presentation/`** — HTTP routers, the FastStream worker, the CLI. Parses,
  dispatches, renders. No business logic, no direct database access.
- **`composition.py`** — the only module that imports every layer. New
  dependency wiring goes here, nowhere else.

## Non-negotiables

- **Never assign to aggregate fields from outside the aggregate.** State
  changes go through domain methods that emit events. `yaddd-linter` rule
  `YDDD001` fails the build otherwise — including in tests.
- **Never mutate an aggregate in a non-domain module** (`YDDD002`).
- **No magic strings.** Any string that carries meaning — a status value, a
  table name, a payload key, a route tag, a CLI command name, a config default,
  an error message, a health-check name — lives in a named constant. Define
  constants close to the concept they name: domain vocabulary in
  `app/domain/*/constants.py`, application wire formats in
  `app/application/*/constants.py`, infrastructure identifiers in
  `app/infrastructure/*/constants.py`, and presentation surface strings in
  `app/presentation/*/constants.py`. Tests reuse the same constants; shared
  test fixtures live in `tests/shared/`.
- **One unit of work per operation.** A handler receives its unit of work
  through the constructor; a `SqlSession` wraps exactly one `AsyncSession`, so
  sharing a unit of work across concurrent requests interleaves transactions.
- **Events are published after commit.** The unit of work does it; hand-written
  `publish()` calls inside a use case are a bug.
- **Never leak a card token.** `CardToken` is sensitive: it must not appear in
  a response body, a log line or a `repr`.
- **Value objects at the edges.** Request schemas, table columns and events use
  the VO type; validation then happens on the way in *and* on the way out.

## Adding a slice

1. `domain/<slice>/` — aggregate, VOs, events, rules, repository port.
2. `application/` — commands, handler, DTOs, mapper, ports, projection.
3. `infrastructure/` — table + repository adapter, or broker adapter.
4. `presentation/` — router/schemas or consumer wiring.
5. `composition.py` — register in `build_container` / `build_command_bus`.
6. Tests: unit for the domain, integration for adapters and HTTP, and contract
   tests inheriting `yaddd.testing.CrudRepositoryContract`,
   `UnitOfWorkContract` and `VoSerializationContract`.

## Tests

- `tests/unit/` — pure logic, no I/O; CLI tested synchronously because
  `WorkerCli.run` owns its event loop.
- `tests/integration/` — real SQLite file per test, the real ASGI apps over
  `httpx.ASGITransport`, and `TestRedisBroker` for consumers.
- `tests/contract/` — inherit from `yaddd.testing`; only the fixtures are
  local, never the assertions.

`pytest` runs in `asyncio_mode = "auto"`: write plain `async def test_...`
without markers.

## Typing

`ty` and `pyright` both run in strict mode over `app` and `tests`.

`yaddd` builds framework classes at runtime, so neither checker can see the
synthesized keyword-only `__init__` of aggregates, commands, events and DTOs.
The resulting `unknown-argument` / `reportCallIssue` noise is suppressed
centrally in `pyproject.toml`, not with inline "magic strings":

```toml
[tool.ty.environment]
python-version = "3.12"

[[tool.ty.overrides]]
include = ["app/**/*.py", "tests/**/*.py"]
rules = { "unknown-argument" = "ignore" }

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "strict"
include = ["app", "tests"]
executionEnvironments = [{ root = ".", reportCallIssue = "none" }]
```

**Rule:** never add file-level type-checker suppression pragmas inside source
files. If a new category of files needs a blanket suppression, change the
checker configuration in `pyproject.toml` and document why.

Style: PEP 695 generics (`class Container[T]`), `X | None` unions, `type` aliases,
line length 120, `ruff format` is the formatter of record.