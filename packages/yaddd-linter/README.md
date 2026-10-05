# yaddd-linter

DDD-aware static analysis for [yaddd](https://github.com/your-repo/yaddd) projects.

## Rules

- **YDDD001** — Direct mutation of an aggregate/entity field outside aggregate methods.
- **YDDD002** — Mutating call on an aggregate attribute outside aggregate methods.
- **YDDD003** — Layer isolation violation between core layers (e.g. domain imports application).
- **YDDD004** — Domain layer imports a third-party module (domain must depend only on stdlib and `yaddd` itself).
- **YDDD005** — A yaddd plugin imports another yaddd plugin (e.g. `yaddd_sqlalchemy` imports `yaddd_pydantic`).

## Usage

```bash
yaddd-linter check packages/yaddd/src
```

The output format is compatible with ruff:

```
packages/yaddd/src/yaddd/application/service.py:42:5: YDDD001 Direct mutation of aggregate field 'status' of variable 'order' outside aggregate methods
```
