# Domain layer: project specifics

Additive to the base domain rules. Never relaxes core rules; on conflict, core
wins.

- **Pydantic at the domain edge:** `PydanticVO` is the sanctioned base for
  value objects that double as request and column types, with constraints
  declared through `pydantic.Field`. The `yaddd-pydantic` extension pack
  sanctions `pydantic` and `yaddd_pydantic`; no other third-party package is
  allowed in this layer.
- **Never leak a card token.** `CardToken` is sensitive: it must not appear in
  a response body, a log line or a `repr`.
