# yaddd-pydantic
Pydantic v2 integration for [yaddd](https://github.com/pyDDD/yaddd).

`PydanticVO[V]` makes yaddd value objects first-class field types in pydantic
models: pydantic constraints double as VO validation, models accept both raw
values and VO instances, dumps produce primitives, and JSON Schema shows the
primitive shape. `SensitiveValueObject` masking is preserved.

Wiring is explicit: subclass `PydanticVO` in your domain, no auto-discovery.
Conformance is proven by `VoSerializationContract` from `yaddd.testing`.
