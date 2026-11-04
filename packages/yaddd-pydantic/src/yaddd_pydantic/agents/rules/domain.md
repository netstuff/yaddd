# Pydantic value objects

Additive to the base domain rules. This pack relaxes exactly one import rule:
the domain may use `pydantic` and `yaddd_pydantic`.

- **Subclass `PydanticVO`** for value objects that double as request and column
  types. It is the sanctioned base, so validation runs on the way in and on the
  way out.
- **Declare constraints with `pydantic.Field`** on the VO's fields rather than
  duplicating validation in schemas or adapters.
- **Do not use arbitrary Pydantic models as domain entities.** The relaxation
  is for value objects, not for persistence models, request DTOs or framework
  wiring.
