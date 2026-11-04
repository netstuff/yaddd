# Tooling and typing

Additive to the core rules. Never relaxes core rules; on conflict, core wins.

- **One quality gate.** Use the project's configured command that runs
  formatting, lint, architecture, strict types and tests.
- **Never add file-level type-checker suppressions inside source files.** If a
  category of files needs a blanket suppression, change the checker
  configuration and document why.
- **Fix the tool instead of restating an enforceable rule in prose.** If a
  rule can be checked mechanically, configure the checker.
- **Do not silence a rule to make a change pass.** Either satisfy the rule or
  record a reasoned local override in `.agents/overrides.toml`.
