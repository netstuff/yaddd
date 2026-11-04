# Testing

Additive to the core rules. Never relaxes core rules; on conflict, core wins.

- **`tests/unit/`** — pure logic, no I/O.
- **`tests/integration/`** — real adapters, real edge transports, real
  infrastructure where practical.
- **`tests/contract/`** — inherit from `yaddd.testing`; only the fixtures are
  local, never the assertions.
- **Run async tests without markers** when the project uses
  `asyncio_mode = "auto"`; write plain `async def test_...`.
- **Reuse the same constants as production code;** shared fixtures live in
  `tests/shared/`.
- **Domain rules still apply in tests:** no external aggregate mutation.
