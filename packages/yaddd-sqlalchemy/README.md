# yaddd-sqlalchemy
SQLAlchemy integration for [yaddd](https://github.com/pyDDD/yaddd).

- `SqlCrudRepository` — SQLAlchemy Core-based implementation of the `CrudRepository` port;
- `SqlUnitOfWork` — `UnitOfWork` over `AsyncSession`;
- `VOTypeDecorator` — `TypeDecorator` persisting `ValueObject` instances as raw values.

Wiring is explicit: instantiate in your composition root, no auto-discovery.
Port conformance is proven by the contract suites in `yaddd.testing`.
