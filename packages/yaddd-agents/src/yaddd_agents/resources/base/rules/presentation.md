# Presentation layer

Additive to the core rules. Never relaxes core rules; on conflict, core wins.

- **Parse → dispatch → render.** No business logic and no direct database
  access; talk to `application` through injected ports.
- **HTTP routers, message consumers and the CLI** each stay thin adapters.
- **Use VO types in request and response schemas** so validation happens at the
  edge.
- **Surface strings live in `presentation/*/constants.py`:** route tags, CLI
  command names, error messages, health-check names.
