# Testing: project specifics

Additive to the base testing rules. Never relaxes core rules; on conflict, core
wins.

- **CLI tests are synchronous** because `WorkerCli.run` owns its event loop.
- **Integration tests use a real SQLite file per test**, the real ASGI apps over
  `httpx.ASGITransport`, and `TestRedisBroker` for consumers.
- **Contract tests inherit from `yaddd.testing`;** only the fixtures are local,
  never the assertions.
