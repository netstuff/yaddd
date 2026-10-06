# yaddd-template

A runnable starting point for a web application on
[`yaddd`](https://github.com/netstuff/yaddd) — DDD ports, aggregates, domain
events — with FastAPI in front, FastStream behind, and SQLAlchemy Core under
both.

One business slice (`orders`) is implemented end to end so every moving part has
a working example. Delete what you do not need; keep the wiring.

## What you get

- **Domain** — `Order` aggregate with invariants, business rules and domain
  events; imports are limited to `yaddd`, `pydantic` and `PydanticVO`.
- **Application** — commands, handlers, DTOs, mappers, repository ports, unit
  of work, projections.
- **Infrastructure** — SQLAlchemy Core adapters, Redis broker, publisher,
  health probes, pydantic-settings configuration.
- **Presentation** — FastAPI router and app factory, FastStream worker,
  operator CLI, health probes for both processes.
- **Tests** — unit, integration (real SQLite, in-memory broker) and contract
  tests inheriting from `yaddd.testing`.
- **Tooling** — strict ty and pyright, Ruff, `yaddd-linter`, Makefile,
  Dockerfile, `.env.example`.

## Quick start

```bash
uv sync                                  # create .venv and install everything
cp .env.example .env                     # then edit YADDD_* values
uv run worker migrate                 # create the schema
uv run api                            # http://localhost:8000/docs
```

In a second terminal:

```bash
uv run worker consume                 # consume events, print projections
uv run worker place-order --reference ORD-1A2B3C4D --total 1999
uv run worker health
```

SQLite is the default so the template runs with no services. Point
`YADDD_DATABASE_URL` at PostgreSQL and `YADDD_BROKER_URL` at Redis (or NATS,
or Kafka — see below) when you need them. `uv.lock` is committed, so the Docker
build is reproducible; run `make lock` after changing dependencies.

## Layout

```
app/
├── domain/            # aggregates, value objects, rules, events, ports — no framework
├── application/       # commands, handlers, DTOs, mappers, uow, projections, health vocabulary
├── infrastructure/    # SQLAlchemy, Redis, settings, logging, probes
├── presentation/
│   ├── api/           # FastAPI: routers, schemas, error mapping, ASGI entrypoint
│   └── worker/        # FastStream consumers, probes, CLI, event drain
└── composition.py     # the only module allowed to import every layer
tests/
├── unit/              # domain, health, envelopes, CLI
├── integration/       # real database, real ASGI apps, in-memory broker
└── contract/          # yaddd.testing contracts for repository, uow and VOs
```

Dependencies point inwards: `presentation → application → domain`.
Infrastructure implements ports declared by the domain. `composition.py`
chooses the concrete implementations; nothing else imports them.

## The three processes

| Process | Command | Serves | Purpose |
|---|---|---|---|
| API | `api` | `:8000` | HTTP, OpenAPI at `/docs` |
| Broker/worker | `broker` | `:8001` | consumes events, probes, AsyncAPI at `/docs/asyncapi` |
| Operator | `worker` | — | `migrate`, `drop-all`, `health`, `place-order`, `consume`, `drain` |

### Health semantics

- `GET /health` — every dependency check, always HTTP 200.
- `GET /health/live` — the process itself, touches nothing, HTTP 200.
- `GET /health/ready` — HTTP 503 while any dependency is `down`.

Point Kubernetes `livenessProbe` at `/health/live` and `readinessProbe` at
`/health/ready`: a slow consumer must not be mistaken for a dead process.

## How an event travels

1. A route dispatches `PlaceOrder` on the command bus.
2. `PlaceOrderHandler` builds the aggregate, saves it and commits.
3. The unit of work publishes `OrderPlaced` **after** a successful commit, so a
   rolled back transaction never announces anything.
4. `BrokerEventPublisher` wraps it in an `EventEnvelope`
   (`event_type`, `occurred_at`, JSON-safe `payload`) and publishes to the Redis
   channel.
5. `OrderPlacedProjector` consumes the envelope and writes the projection row.

The projection is idempotent, so a redelivered event is a no-op.

> **At-least-once, not exactly-once.** Publishing happens after the commit and
> without an outbox: if the broker is unreachable at that moment, the order is
> saved but never announced. `BrokerEventPublisher` logs
> `failed to publish <Event> to channel <channel>` — grep it, or add an outbox
> table before you need the guarantee.

## Configuration

Every setting is a field of `infrastructure.config.settings.Settings`, read
from the environment or a `.env` file with the `YADDD_` prefix — see
[`.env.example`](.env.example).

| Variable | Default | Meaning |
|---|---|---|
| `YADDD_APP_NAME` | `yaddd-template` | appears in logs, OpenAPI title, AsyncAPI title |
| `YADDD_APP_ENV` | `local` | one of `local`, `test`, `staging`, `production` |
| `YADDD_LOG_LEVEL` | `INFO` | standard library log level |
| `YADDD_DATABASE_URL` | `sqlite+aiosqlite:///./yaddd-template.db` | SQLAlchemy async URL |
| `YADDD_DB_ECHO` | `false` | log every SQL statement |
| `YADDD_BROKER_URL` | `redis://localhost:6379/0` | FastStream broker URL |
| `YADDD_BROKER_EVENTS_CHANNEL` | `domain-events` | pub/sub channel of domain events |
| `YADDD_API_HOST` / `YADDD_API_PORT` | `0.0.0.0` / `8000` | API bind address |
| `YADDD_API_WORKERS` | `1` | uvicorn workers of the API process |
| `YADDD_WORKER_HOST` / `YADDD_WORKER_PORT` | `0.0.0.0` / `8001` | worker bind address |
| `YADDD_PROBE_TIMEOUT` | `2.0` | per-check timeout, seconds |

## Making it yours

- **Another slice** — add `domain/<slice>`, `application` use cases, adapters
  and routes; register handlers in `composition.build_command_bus`.
- **Another broker** — replace `infrastructure.messaging.broker.make_broker`.
  Kafka, NATS and RabbitMQ are one function; nothing above it changes.
- **Another database** — any async SQLAlchemy dialect. `VOTypeDecorator` keeps
  value objects validated on the way in *and* out.
- **Delete the sample slice** — remove `domain/orders`,
  `application/{commands,handlers,dto,mappers,projections}.py` and the orders
  routes, then delete their tests. The wiring patterns stay.

## Quality gates

```bash
make check        # ruff + ty + pyright + pytest + yaddd-linter
make fmt          # ruff format
make test         # pytest
```

`make lint` runs the architecture linter:

```
yaddd-linter app tests
```

It is not on PyPI yet, so install it once from a checkout of the yaddd
repository: `uv tool install ./packages/yaddd-linter` (or, from this
directory inside the monorepo, `uv pip install ../../yaddd-linter`).

It enforces the architectural rules: no assignment to
aggregate fields from outside (`YDDD001`), no aggregate mutation in
non-domain modules (`YDDD002`), no layer-crossing imports (`YDDD003`), no
third-party imports in the domain beyond the pydantic serialization stack
(`YDDD004`), no plugins importing plugins (`YDDD005`).

### A note on type checking

`yaddd` builds its framework classes at runtime (keyword-only dataclasses), and
neither ty nor pyright can see the synthesized `__init__`. The resulting
`unknown-argument` / `reportCallIssue` noise is suppressed centrally in
`pyproject.toml` (see `[tool.ty.overrides]` and `executionEnvironments`), not
with inline pragmas. Everything else is checked under `strict` in both checkers.

## Docker

```bash
docker build -t yaddd-template .
docker run --rm -p 8000:8000 -p 8001:8001 --env-file .env yaddd-template
```

The image runs the API by default; override with
`docker run … broker` or `… worker <command>`.