# yaddd

Yet another DDD for Python.

`yaddd` is a framework-agnostic, strictly typed toolkit for layered DDD
applications. The core has no runtime dependencies; integrations with
SQLAlchemy, Pydantic, linters, AI-agent rules, and diagram tooling ship as
separate distributions in this monorepo.

- **Domain** — entities, aggregate roots, value objects, domain events,
  factories, specifications, business rules, domain services.
- **Application** — commands, queries, handlers, DTOs, mappers, event
  publishers, unit-of-work ports, scenario runner.
- **Infrastructure** — repository ports and in-memory implementations,
  read models, transactions, connectors.
- **Presentation** — CLI, HTTP, GraphQL ports and request/response objects.

Start with [SPEC.md](SPEC.md) for the layer contracts and the DDD glossary
([§15](SPEC.md#15-глоссарий-ddd-терминов)).

## Requirements

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/) for the monorepo and the template
- SQLite is the default template database, so no PostgreSQL is required. A
  broker is only needed for event consumption; the default is Redis.

## Repository layout

```text
.
├── packages/
│   ├── yaddd/                 # core library, zero runtime dependencies
│   ├── yaddd-sqlalchemy/      # SQLAlchemy Core + AsyncSession integration
│   ├── yaddd-pydantic/        # Pydantic v2 value-object integration
│   ├── yaddd-linter/          # DDD-aware static analysis + LSP
│   ├── yaddd-agents/          # layered AGENTS.md rule generator
│   ├── yaddd-utils/           # scenario inspection and Mermaid rendering
│   └── yaddd-example/        # runnable FastAPI + FastStream application
├── scripts/standalone.py      # copy the template out of the monorepo
├── docs/                      # additional documentation
├── SPEC.md
└── Makefile                   # `make standalone NAME=...`
```

### Packages

| Package | Version | Purpose | Install |
|---|---:|---|---|
| `yaddd` | 0.5.0 | Core DDD building blocks; zero dependencies | `pip install yaddd` |
| `yaddd-sqlalchemy` | 0.2.0 | `SqlCrudRepository`, `SqlUnitOfWork`, `VOTypeDecorator` | `pip install yaddd-sqlalchemy` |
| `yaddd-pydantic` | 0.2.0 | `PydanticVO` value objects as Pydantic fields | `pip install yaddd-pydantic` |
| `yaddd-linter` | 0.2.0 | `YDDD001`–`YDDD005` checks and an LSP server | `pip install yaddd-linter` |
| `yaddd-agents` | 0.1.0 | Generates and verifies layered agent rules | `pip install yaddd-agents` |
| `yaddd-utils` | 0.1.0 | Scenario inspection and Mermaid diagrams | `pip install yaddd-utils` |
| `yaddd-example` | 0.3.0 | Reference application, copied out per project | see [Template](#template) |

`yaddd-example` is intentionally excluded from the root workspace and keeps its
own `uv.lock`; the other packages are workspace members. The template is not a
library to depend on — copy it with `make standalone`.

## Installation

### Work on this repository

```bash
uv sync                     # workspace + all dependency groups
uv run pytest               # all package tests
```

### Use the packages in an application

With `uv`:

```bash
uv add yaddd yaddd-sqlalchemy yaddd-pydantic
uv add --dev yaddd-linter yaddd-agents
```

With `pip`:

```bash
pip install yaddd yaddd-sqlalchemy yaddd-pydantic
pip install yaddd-linter yaddd-agents
```

Until a package is available on PyPI, install it from this checkout:

```bash
uv tool install ./packages/yaddd-linter
uv pip install -e ./packages/yaddd-agents
```

## Core: `yaddd`

The core public surface is exported from one module:

```python
from yaddd import AggregateRoot, Command, DomainEvent, UnitOfWork, ValueObject
```

### Quickstart

```python
import asyncio
from uuid import UUID, uuid4

from yaddd import (
    AggregateRoot,
    BusinessRule,
    Command,
    DomainEvent,
    HttpRequest,
    HttpResponse,
    InMemoryCrudRepository,
    InMemoryEventPublisher,
)


class PositiveTotal(BusinessRule):
    message = "total must be positive"

    def is_satisfied_by(self, candidate: "Order") -> bool:
        return candidate.total > 0


class OrderPlaced(DomainEvent):
    order_id: UUID


class Order(AggregateRoot):
    id: UUID
    total: int

    INVARIANTS = (PositiveTotal(),)

    def place(self) -> None:
        self.add_event(OrderPlaced(order_id=self.pk))


class PlaceOrder(Command):
    total: int


class PlaceOrderHandler:
    def __init__(self, orders: InMemoryCrudRepository[Order], publisher: InMemoryEventPublisher) -> None:
        self._orders = orders
        self._publisher = publisher

    async def handle(self, command: PlaceOrder) -> UUID:
        order = Order(id=uuid4(), total=command.total)
        order.place()
        await self._orders.create(order)
        await self._publisher.publish(order.pull_events())
        return order.pk


class PlaceOrderHttpHandler:
    def __init__(self, handler: PlaceOrderHandler) -> None:
        self._handler = handler

    async def handle(self, request: HttpRequest) -> HttpResponse:
        order_id = await self._handler.handle(PlaceOrder(total=int(request.body.decode())))
        return HttpResponse(status=201, body=str(order_id).encode())


async def on_order_placed(event: DomainEvent) -> None:
    print(f"event published: {event}")


async def main() -> None:
    publisher = InMemoryEventPublisher()
    publisher.subscribe(OrderPlaced, on_order_placed)
    orders = InMemoryCrudRepository[Order]()
    http = PlaceOrderHttpHandler(PlaceOrderHandler(orders, publisher))

    response = await http.handle(HttpRequest(method="POST", path="/orders", body=b"100"))
    print(response.status, response.body.decode())


if __name__ == "__main__":
    asyncio.run(main())
```

The example publishes events manually because it uses an in-memory repository.
In a real application, use a unit of work: it commits first and publishes the
events of tracked aggregates only after a successful commit.

### What is in the core

| Area | Main types |
|---|---|
| Domain | `Entity`, `AggregateRoot`, `ValueObject`, `SensitiveValueObject`, `DomainEvent`, `BusinessRule`, `Specification`, `DomainService`, `Factory`, `CrudRepository` |
| Application | `Command`, `Query`, `CommandHandler`, `QueryHandler`, `DTO`, `Mapper`, `ApplicationService`, `EventPublisher`, `UnitOfWork`, `Scenario`, `ScenarioRunner` |
| Infrastructure | `InMemoryCrudRepository`, `ReadModel`, `ReadModelRepository`, `BaseTransaction`, `MultiTransaction`, `Connector` |
| Presentation | `HttpRequest`, `HttpResponse`, `HttpHandler`, `CliCommand`, `Resolver` |
| Errors | `YadddError`, `DomainError`, `ApplicationError`, `InfrastructureError`, `ValidationError`, `InvariantViolationError`, `EntityNotFoundError`, `ConflictError` |

### Port contract tests

`yaddd.testing` contains reusable pytest suites for adapter authors:

```python
from yaddd.testing import CrudRepositoryContract, UnitOfWorkContract, VoSerializationContract
```

Subclass a contract in your plugin's test suite and override its fixtures. The
contracts are intentionally not re-exported from the top-level package because
importing `yaddd.testing` pulls in `pytest`.

## SQLAlchemy integration: `yaddd-sqlalchemy`

```bash
pip install yaddd-sqlalchemy
```

The package provides:

- `SqlCrudRepository` — SQLAlchemy Core implementation of `CrudRepository`;
- `SqlTransactionBoundRepository` — a repository bound to the active
  `SqlTransaction`, which tracks aggregates for post-commit event publishing;
- `SqlSession` / `SqlTransaction` — session and transaction adapters;
- `SqlUnitOfWork` — `UnitOfWork` over one `AsyncSession`;
- `VOTypeDecorator` — persists `ValueObject` instances as raw values.

### Repository and unit of work

```python
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from yaddd import AggregateRoot, DomainEvent, InMemoryEventPublisher
from yaddd_sqlalchemy import (
    SqlSession,
    SqlTransaction,
    SqlTransactionBoundRepository,
    SqlUnitOfWork,
)


metadata = MetaData()
orders_table = Table(
    "orders",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("status", String(16), nullable=False),
    Column("total", Integer, nullable=False),
)


class Order(AggregateRoot):
    id: str
    status: str
    total: int


class OrderPlaced(DomainEvent):
    order_id: str


class OrderRepository(SqlTransactionBoundRepository[Order]):
    table = orders_table

    def to_domain(self, row: Row[Any]) -> Order:
        return Order(id=str(row.id), status=str(row.status), total=int(row.total))

    def to_row(self, instance: Order) -> dict[str, Any]:
        return {"id": instance.pk, "status": instance.status, "total": instance.total}


@dataclass
class Repositories:
    orders: OrderRepository


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///./app.db")
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)

    session = SqlSession(async_sessionmaker(engine, expire_on_commit=False))
    transaction = SqlTransaction(session, InMemoryEventPublisher())
    repositories = Repositories(orders=OrderRepository(transaction))
    uow = SqlUnitOfWork(transaction, repositories)

    async with uow:
        order = Order(id="ORD-1", status="new", total=1999)
        order.add_event(OrderPlaced(order_id=order.pk))
        await uow.repos.orders.create(order)
        await uow.commit()  # persists, then publishes tracked events

    await engine.dispose()
```

Notes:

- Repositories never commit; transaction boundaries belong to the unit of work.
- `IntegrityError` is translated to `yaddd.ConflictError`; map it to HTTP 409 at
  the presentation boundary.
- Primary keys must be single-column and natively bindable by the column type.
- Use `VOTypeDecorator` for value-object columns:

```python
from sqlalchemy import String

from yaddd import ValueObject
from yaddd_sqlalchemy import VOTypeDecorator


class Email(ValueObject[str]):
    @classmethod
    def validate(cls, value: str) -> str:
        return value.strip().lower()


class EmailType(VOTypeDecorator):
    impl = String(255)
    cache_ok = True
    vo_class = Email
```

## Pydantic integration: `yaddd-pydantic`

```bash
pip install yaddd-pydantic
```

`PydanticVO` makes a value object usable directly as a Pydantic field type.
Pydantic constraints become VO validation, models accept raw values or VO
instances, dumps produce primitives, and JSON Schema exposes the primitive
shape.

```python
from typing import Annotated

from pydantic import BaseModel, Field

from yaddd import SensitiveValueObject
from yaddd_pydantic import PydanticVO


class PositiveTotal(PydanticVO[int]):
    pydantic_type = Annotated[int, Field(gt=0)]


class Password(SensitiveValueObject[str], PydanticVO[str]):
    pydantic_type = Annotated[str, Field(min_length=8)]


class OrderModel(BaseModel):
    total: PositiveTotal
    password: Password


order = OrderModel(total=1999, password="super-secret-1")
assert isinstance(order.total, PositiveTotal)
assert order.model_dump() == {"total": 1999, "password": "super-secret-1"}
assert "super-secret-1" not in repr(order)  # sensitive payload is masked
```

Subclass `PydanticVO` in the domain layer. No auto-discovery or registration is
required; the integration is explicit.

## Linter: `yaddd-linter`

```bash
pip install yaddd-linter
yaddd-linter app tests
```

### Rules

| Code | Meaning |
|---|---|
| `YDDD001` | Direct mutation of an aggregate/entity field outside aggregate methods |
| `YDDD002` | Mutating call on an aggregate attribute outside aggregate methods |
| `YDDD003` | Layer-isolation violation (for example, domain imports application) |
| `YDDD004` | Domain imports a third-party module not allowed by policy |
| `YDDD005` | One yaddd plugin imports another yaddd plugin |

### CLI

```bash
yaddd-linter [OPTIONS] PATHS...
```

| Option | Meaning |
|---|---|
| `--format {text,json}` | Output format, default `text` |
| `--stdin-filename PATH` | Filename used for layer detection when reading stdin |
| `--select CODES` | Comma-separated rules to enable |
| `--ignore CODES` | Comma-separated rules to disable |
| `--config PATH` | Path to `pyproject.toml` with `[tool.yaddd-linter]` |
| `--layers-config PATH` | Path to `.yaddd/layers.json` with per-layer import policies |
| `--version` | Print the version |

Exit codes: `0` — clean, `1` — violations, `2` — CLI/configuration error.

Examples:

```bash
yaddd-linter app tests
yaddd-linter --select YDDD003,YDDD004 --format json app
echo "from yaddd.application import Command" \
  | yaddd-linter --stdin-filename app/domain/order.py -
```

### Configuration

```toml
[tool.yaddd-linter]
select = ["YDDD001", "YDDD002", "YDDD003", "YDDD004", "YDDD005"]
ignore = ["YDDD004"]
```

Layer policy is read from `.yaddd/layers.json` next to `pyproject.toml` (or from
`--layers-config`). The file is generated by `yaddd-agents`; its schema is:

```json
{
  "schema": 1,
  "layers": {
    "domain": {
      "imports": ["domain"],
      "third_party": ["pydantic", "yaddd_pydantic"]
    }
  }
}
```

Without `.yaddd/layers.json`, the linter keeps the legacy layer rules.

### LSP

```bash
yaddd-linter-lsp
```

The server communicates over stdio and refreshes diagnostics on open, change,
and save. It reads the same `[tool.yaddd-linter]` configuration.

## Agent rules: `yaddd-agents`

```bash
pip install yaddd-agents
```

`yaddd-agents` keeps `AGENTS.md` and the per-layer rule files in sync with the
installed `yaddd-*` packages. Core rules always live in the root `AGENTS.md`;
layer files are additive and read lazily. On conflict, core wins.

### Commands

```bash
yaddd-agents init              # create .agents/, .yaddd/, and the managed block
yaddd-agents sync              # regenerate files from active packs
yaddd-agents check             # fail when generated files are stale
yaddd-agents explain RULE_ID   # show where a rule comes from
yaddd-agents list --json       # machine-readable rule list
```

Global options: `--root PATH` selects the project root and `--workspace PATH`
enables discovery of editable extension packs in a monorepo.

### Generated files

```text
.agents/rules/base/                 # copied from yaddd-agents
.agents/rules/extensions/<pack>/    # copied from extension packages
.agents/rules/local/                # hand-written, never overwritten
.agents/manifest.lock.json          # pack versions and content hashes
.yaddd/layers.json                  # machine policy for yaddd-linter
AGENTS.md                           # managed block between markers
```

Recommended workflow:

1. Edit project-specific rules in `.agents/rules/local/`.
2. Put explicit allow/deny overrides in `.agents/overrides.toml`.
3. Run `yaddd-agents sync`.
4. Run `yaddd-agents check` in CI.

Overrides are explicit and require a reason:

```toml
[[relaxes]]
rule = "IMPORTS_INFRASTRUCTURE"
allow_add = ["redis", "sqlalchemy"]
reason = "Infrastructure adapters implement the broker and persistence ports."

[[restricts]]
rule = "IMPORTS_APPLICATION"
deny_add = ["presentation"]
reason = "Application code must not depend on the edge."
```

The resolver also supports `replaces` and `disables`; a deny always wins over an
allow, and `replace`/`disable` operations must include a reason.

### Extension packs

An extension pack is a distribution whose module contains
`agents/manifest.toml` and `agents/rules/*.md`. `yaddd-agents` discovers it from
project dependencies or from an explicit mapping:

```toml
[tool.yaddd.agents.extensions]
my-extension = "my_extension/agents/manifest.toml"
```

No entry points or global registries are used.

## Utilities: `yaddd-utils`

```bash
pip install yaddd-utils
```

`yaddd-utils` inspects `Scenario` subclasses and renders Mermaid diagrams.

```bash
# Flowchart (default)
yaddd-mermaid myapp.scenarios --output diagram.mmd

# Other renderers
yaddd-mermaid myapp.scenarios --renderer graph --direction LR
yaddd-mermaid myapp.scenarios --renderer sequence --show-levels

# Also render an image through mermaid-py
yaddd-mermaid myapp.scenarios --output diagram.mmd --image diagram.svg
```

Python API:

```python
from yaddd_utils.inspect import ScenarioAnalyzer
from yaddd_utils.mermaid import RenderOptions, ScenarioRenderer

scenarios = ScenarioAnalyzer().analyze_module("myapp.scenarios")
diagram = ScenarioRenderer(RenderOptions(direction="TD")).render_infos(scenarios)
print(diagram)
```

## Template: `yaddd-example`

The template is a runnable web application with one complete `orders` slice. It
uses FastAPI in front, FastStream behind, and SQLAlchemy Core under both.

```bash
cd packages/yaddd-example
uv sync --all-groups
cp .env.example .env
uv run worker migrate
uv run api                     # http://localhost:8000/docs
```

In another terminal:

```bash
uv run broker                  # worker process, AsyncAPI at :8001/docs/asyncapi
uv run worker consume          # consume events in the foreground
uv run worker place-order --reference ORD-1A2B3C4D --total 1999
uv run worker health           # exit code 1 when not ready
```

### What is included

- **Domain** — `Order` aggregate, invariants, business rules, domain events,
  value objects, repository ports.
- **Application** — commands, handlers, DTOs, mappers, unit of work,
  projections, health vocabulary.
- **Infrastructure** — SQLAlchemy adapters, Redis/FastStream broker,
  publisher, settings, logging, probes.
- **Presentation** — FastAPI app and routers, FastStream worker, operator CLI.
- **Tests** — unit, integration, and contract suites based on `yaddd.testing`.
- **Tooling** — Ruff, ty, Pyright, `yaddd-linter`, generated `yaddd-agents`
  rules, Makefile, Dockerfile.

### Processes

| Process | Command | Purpose |
|---|---|---|
| API | `uv run api` | HTTP API, OpenAPI at `/docs` |
| Broker/worker | `uv run broker` | consumes events, probes, AsyncAPI |
| Operator | `uv run worker ...` | `migrate`, `drop-all`, `health`, `place-order`, `consume`, `drain` |

Health endpoints:

- `GET /health` — every dependency check, always HTTP 200;
- `GET /health/live` — process liveness, no dependency calls;
- `GET /health/ready` — HTTP 503 while any dependency is down.

### Configuration

All settings use the `YADDD_` prefix and are read from the environment or
`.env`. See [`packages/yaddd-example/.env.example`](packages/yaddd-example/.env.example).

| Variable | Default |
|---|---|
| `YADDD_APP_NAME` | `yaddd-example` |
| `YADDD_APP_ENV` | `local` |
| `YADDD_LOG_LEVEL` | `INFO` |
| `YADDD_DATABASE_URL` | `sqlite+aiosqlite:///./yaddd-example.db` |
| `YADDD_DB_ECHO` | `false` |
| `YADDD_BROKER_URL` | `redis://localhost:6379/0` |
| `YADDD_BROKER_EVENTS_CHANNEL` | `domain-events` |
| `YADDD_API_HOST` / `YADDD_API_PORT` | `0.0.0.0` / `8000` |
| `YADDD_API_WORKERS` | `1` |
| `YADDD_WORKER_HOST` / `YADDD_WORKER_PORT` | `0.0.0.0` / `8001` |
| `YADDD_PROBE_TIMEOUT` | `2.0` |

SQLite is the default. To switch, install the matching driver or broker extra
first, then set the URL:

```bash
uv add asyncpg                          # PostgreSQL
uv add "faststream[nats]"               # NATS (similarly kafka / rabbitmq)
```

Set `YADDD_DATABASE_URL` and `YADDD_BROKER_URL` accordingly.

### Make targets

```bash
make install       # uv sync --all-groups
make fmt           # format and fix imports
make agents        # regenerate agent rules
make agents-check  # verify generated rules are current
make lint          # formatting, lint, architecture
make types         # ty + pyright
make test          # pytest
make check         # all quality gates
make migrate       # create tables
make api           # run the API
make broker        # run the broker process
make consume       # consume events
make health        # health report
make docker-build  # build the image
```

`make lint` calls the globally installed `yaddd-linter`. Inside this monorepo,
install it into the template environment first:

```bash
uv pip install -e ../yaddd-linter
```

### Docker

```bash
docker build -t yaddd-example .
docker run --rm -p 8000:8000 -p 8001:8001 \
  -v yaddd-data:/data \
  --env-file .env \
  -e YADDD_DATABASE_URL=sqlite+aiosqlite:////data/yaddd-example.db \
  yaddd-example
```

The image sets `/data` as the SQLite location by default; the extra
`YADDD_DATABASE_URL` above keeps that path even when `.env` overrides it.
Override the command for the broker or CLI:

```bash
docker run --rm yaddd-example broker
docker run --rm yaddd-example worker migrate
```

## Standalone template copy

Use the root Makefile to copy the template out of the monorepo. The script:

- rewrites `project.name`, `YADDD_APP_NAME`, the SQLite file, Docker image name,
  README references, and the package docstring;
- removes monorepo-only `[tool.uv.sources]`;
- ignores `.venv`, caches, build artifacts, and `uv.lock`.

```bash
make standalone NAME=acme-orders
# or
make standalone NAME=acme-orders OUTPUT=../acme-orders
```

Then, for the default `dist/<name>` output:

```bash
cd dist/acme-orders
uv lock
make install
make check
```

For a custom `OUTPUT`, `cd` into that directory instead.

Until the packages are published, use a local wheelhouse or temporarily add path
sources to the generated `pyproject.toml` for an offline trial.

## Development

```bash
uv sync                     # workspace and all dependency groups
uv run pytest               # all package tests
uv run ruff check .         # lint
uv run ty check packages/*/src
uv run pyright
```

Formatting:

```bash
uv run ruff format .
```

The template has its own environment and quality gate:

```bash
cd packages/yaddd-example
uv sync --all-groups
uv pip install -e ../yaddd-linter
PATH="$PWD/.venv/bin:$PATH" make check
```

## Publishing

The GitHub Actions workflow `.github/workflows/pypi-publish.yml` publishes every
workspace package on a GitHub release using PyPI Trusted Publishing. The package
matrix includes `yaddd`, `yaddd-linter`, `yaddd-agents`, `yaddd-sqlalchemy`,
`yaddd-pydantic`, and `yaddd-utils`.

Before a release:

```bash
uv run pytest
uv run ruff check .
uv run ty check packages/*/src
uv run pyright
uv build --all-packages
```

## Documentation

- [SPEC.md](SPEC.md) — layer contracts, architectural rules, glossary.
- Per-package READMEs: [`yaddd`](packages/yaddd/README.md),
  [`yaddd-sqlalchemy`](packages/yaddd-sqlalchemy/README.md),
  [`yaddd-pydantic`](packages/yaddd-pydantic/README.md),
  [`yaddd-linter`](packages/yaddd-linter/README.md),
  [`yaddd-agents`](packages/yaddd-agents/README.md),
  [`yaddd-utils`](packages/yaddd-utils/README.md),
  [`yaddd-example`](packages/yaddd-example/README.md).

## License

MIT. See [LICENSE](LICENSE).
