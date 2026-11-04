# Domain layer

Additive to the core rules. Never relaxes core rules; on conflict, core wins.

- **Imports:** stdlib, `yaddd`, and the project's own domain layer only.
  Third-party packages are not allowed unless an active extension pack
  explicitly sanctions them (`YDDD004`).
- **Aggregates live in `domain/<slice>/aggregates/`**, one aggregate per
  module. The module name matches the aggregate name in snake_case:
  `aggregates/order.py` for `Order`.
- **Business-rule names are imperative.** A rule describes the constraint that
  must hold: `TotalMustBePositive` or `OrderMustBePlaced`, never
  `PositiveTotal` or `PlacedOnly`. A rule is a small object with
  `is_satisfied_by`, a `message`, and `&`/`|` composition. Put invariants in
  `INVARIANTS`; put behavioural rules on the aggregate as `ClassVar` instances.
- **Rules declare the state they need as a `Protocol`**, not by importing the
  aggregate. `aggregates` imports `rules`, never the other way round.
- **State changes go through aggregate methods that emit events.** Never assign
  to aggregate fields from outside, including in tests.
- **Domain vocabulary lives in `domain/<slice>/constants.py`**, close to the
  concept it names.
