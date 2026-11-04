# Application layer

Additive to the core rules. Never relaxes core rules; on conflict, core wins.

- **Framework free:** may import `yaddd`, the domain layer and its own layer.
  Do not import presentation frameworks, database drivers or broker clients.
- **Prefer handler shapes in this order:**
  1. A plain `callable` for one-step, stateless business logic.
  2. A `Scenario` subclass when the use case has multiple steps that share a
     mutable `Context` and may branch or skip steps conditionally.
  3. A `class` implementing `CommandHandler` only when the previous two shapes
     do not fit; this should be rare.
- **Encapsulate step business logic in reusable callables.** A `Scenario` step
  is a thin adapter that delegates to a standalone callable — a function or a
  class with `async def __call__`. The callable owns the business logic, can be
  reused across scenarios, and keeps scenario methods free of deep domain
  orchestration.
- **Contents:** commands, handlers (`@command_handler`), DTOs, mappers, the
  unit-of-work port, projections, scenarios and the health vocabulary.
- **Unit of work:** receive it through the constructor; one per operation, never
  shared across concurrent requests. Publish only through the unit of work,
  after commit.
- **Application wire formats** — payload keys, command names, health
  vocabulary — live in `application/*/constants.py`.
