# SQLAlchemy persistence

Additive to the base infrastructure rules. This pack relaxes exactly one import
rule: infrastructure may use `sqlalchemy` and `yaddd_sqlalchemy`.

- **Use `SqlCrudRepository`** for Core-based repositories and
  `SqlUnitOfWork` for transaction boundaries. Do not commit inside a
  repository.
- **Use `VOTypeDecorator`** for columns that hold value objects, so values are
  validated on the way in and on the way out.
- **Keep SQLAlchemy out of `application`.** The pack also restricts that layer:
  use cases depend on ports, not sessions or tables.
