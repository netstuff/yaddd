# Presentation layer: project specifics

Additive to the base presentation rules. Never relaxes core rules; on conflict,
core wins.

- **HTTP routers, the FastStream worker and the CLI** each stay thin adapters.
- **Framework boundary:** FastAPI, Starlette, FastStream, Redis and Uvicorn are
  allowed here only; application and domain stay framework free.
