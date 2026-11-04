# Infrastructure layer: project specifics

Additive to the base infrastructure rules. Never relaxes core rules; on
conflict, core wins.

- **Owns** SQLAlchemy Core tables and adapters, the Redis broker, publisher,
  probes, settings and logging.
- **Table columns use the VO type and `VOTypeDecorator`**, so values are
  validated on the way in *and* out.
