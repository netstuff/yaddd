# yaddd
Yet another DDD for Python

Framework-agnostic (in base) simple library which provides a base layers for building DDD applications:
- Domain layer (DomainServices, AggregateRoots, Entities, ValueObjects, DomainEvent, Factories, Specifications, Rules)
- Application layer (ApplicationServices, Commands, Handlers, DTO, Mappers)
- Infrastructure layer (Repositories, ReadModels)
- Presentation layer (CLI, HTTP, GraphQL)

## Terms and definitions
First, read [Domain Driven Thesaurus](SPEC.md#14-глоссарий-ddd-терминов)


## Installation
You can choose any modern one dependencies manager like a:
`uv sync` or `poetry install` (only poetry >= 2.0)

Also you can choose optional dependencies for `yaddd` wich enable integration with third-part libraries:
1. `yaddd[sqlalchemy]` — supports type decorators in `ValueObject`
