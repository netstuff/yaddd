# Core rules

These rules apply to every task in this repository. They are intentionally
small; layer files add the details for the part of the codebase you touch.

## Architecture

Dependencies point inwards: `presentation → application → domain`.
`infrastructure` implements ports declared by `domain` and `application`.
Composition code is the only place that wires every layer together; new
wiring goes there, nowhere else.

## Core non-negotiables

- **Aggregate state changes only through domain methods** that emit events.
  Never assign to aggregate fields from outside the aggregate.
- **No magic strings.** Any meaningful string — status value, table name,
  payload key, route tag, CLI command name, config default, error message,
  health-check name — is a named constant close to the concept it names.
- **One unit of work per operation.** A handler receives its unit of work
  through the constructor. Never share a unit of work across concurrent
  requests; that interleaves transactions.
- **Events are published after commit.** The unit of work does it. A
  hand-written publish call inside a use case is a bug.
- **Value objects at the edges.** Request schemas, table columns and events
  use the VO type, so validation happens on the way in and on the way out.
- **No inline type-checker pragmas.** Suppress centrally in the project
  configuration and document why; see the tooling rules.

## Where things live

| Path | Responsibility |
|---|---|
| `domain/` | Aggregates, entities, VOs, events, rules, repository ports |
| `application/` | Commands, handlers, DTOs, mappers, UoW port, projections, scenarios |
| `infrastructure/` | Adapters, persistence, messaging, probes, settings, logging |
| `presentation/` | HTTP routers, consumers, CLI |
| `tests/` | Unit, integration and contract tests; shared fixtures |
| composition | Container and command-bus wiring |

## Adding or changing a slice

1. `domain/<slice>/` — aggregate, VOs, events, rules, repository port.
2. `application/` — commands, handler, DTOs, mapper, ports, projection.
3. `infrastructure/` — repository adapter, broker adapter, or other port.
4. `presentation/` — router/schemas or consumer wiring.
5. Composition — register the new wiring.
6. Tests: unit for the domain, integration for adapters and the edge,
   contract tests for ports.

## Verification

Run the project's single quality gate before calling work done. It should
cover formatting, lint, architecture, strict types and tests. Do not report
success based on a subset of the gate.
