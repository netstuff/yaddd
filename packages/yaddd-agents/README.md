# yaddd-agents

Generates and verifies the layered rule set used by AI coding agents in
projects built on `yaddd`.

The package is intentionally generic: it knows about DDD layers, not about
FastAPI, Redis or any other application framework. Framework-specific rules
come from extension packages (`yaddd-pydantic`, `yaddd-sqlalchemy`, …) and
from the project's own `.agents/rules/local/` directory.

## Commands

```bash
yaddd-agents init              # create .agents/, .yaddd/ and the managed block
yaddd-agents sync              # rebuild generated files from active packs
yaddd-agents check             # fail when generated files are stale
yaddd-agents explain RULE_ID   # show where a rule comes from
yaddd-agents list --json       # machine-readable rule list
```

Generated paths:

```
.agents/rules/base/                 # copied from yaddd-agents
.agents/rules/extensions/<pack>/    # copied from extension packages
.agents/rules/local/                # hand-written, never overwritten
.agents/manifest.lock.json          # pack versions and content hashes
.yaddd/layers.json                  # machine config for yaddd-linter
AGENTS.md                           # managed block between markers
```

## Extension packs

An extension pack is a distribution whose module contains
`agents/manifest.toml` and `agents/rules/*.md`. `yaddd-agents` discovers it
from the project's dependencies or from an explicit mapping:

```toml
[tool.yaddd.agents.extensions]
my-extension = "my_extension/agents/manifest.toml"
```

No entry points or registries are used, matching the yaddd plugin contract.
