# yaddd-linter

DDD-aware static analysis for [yaddd](https://github.com/your-repo/yaddd) projects.

## Rules

- **YDDD001** — Direct mutation of an aggregate/entity field outside aggregate methods.
- **YDDD002** — Mutating call on an aggregate attribute outside aggregate methods.
- **YDDD003** — Layer isolation violation between core layers (e.g. domain imports application).
- **YDDD004** — Domain layer imports a third-party module (domain must depend only on
  stdlib, `yaddd` itself, and the pydantic serialization stack behind `PydanticVO`,
  which is documented as a domain base class).
- **YDDD005** — A yaddd plugin imports another yaddd plugin (e.g. `yaddd_sqlalchemy` imports `yaddd_pydantic`).

## Usage

```bash
yaddd-linter packages/yaddd/src
```

The default output format is compatible with ruff:

```
packages/yaddd/src/yaddd/application/service.py:42:5: YDDD001 Direct mutation of aggregate field 'status' of variable 'order' outside aggregate methods
```

## CLI options

```
yaddd-linter [OPTIONS] PATHS...

Options:
  --format {text,json}   Output format (default: text).
  --stdin-filename PATH  Filename to use when reading from stdin.
  --select CODES         Comma-separated rule codes to enable.
  --ignore CODES         Comma-separated rule codes to disable.
  --config PATH          Path to pyproject.toml with [tool.yaddd-linter].
  --version              Show version and exit.
```

## Configuration

`yaddd-linter` reads configuration from the nearest `pyproject.toml`:

```toml
[tool.yaddd-linter]
select = ["YDDD001", "YDDD003"]
ignore = ["YDDD004"]
exclude = ["**/migrations/**"]
```

CLI flags `--select` and `--ignore` override the configuration file.

## Exit codes

- `0` — no violations found.
- `1` — one or more violations found.
- `2` — CLI or configuration error.

## JSON output

Use `--format json` to emit a machine-readable array:

```bash
echo "from yaddd.application.commands import CreateOrder" \
  | yaddd-linter --stdin-filename app/domain/order.py --format json -
```

```json
[
  {
    "path": "app/domain/order.py",
    "line": 1,
    "col": 0,
    "code": "YDDD003",
    "message": "domain layer imports from application layer: 'yaddd.application.commands'"
  }
]
```

## LSP server

`yaddd-linter` includes a Language Server Protocol server for live diagnostics
in editors.

Start it manually:

```bash
yaddd-linter-lsp
```

The server communicates over stdio and updates diagnostics on:

- `textDocument/didOpen`
- `textDocument/didChange`
- `textDocument/didSave`

Diagnostics are cleared on `textDocument/didClose`.

### Editor setup

- **VSCode**: create an extension that launches `yaddd-linter-lsp` and connects
  via `vscode-languageclient`.
- **Zed**: register `yaddd-linter-lsp` as a language server for Python in
  `settings.json`.
- **JetBrains**: use LSP4IJ or a small plugin that starts `yaddd-linter-lsp`.
- **Neovim / Emacs**: configure the server with your LSP client.

The LSP server reads the same `[tool.yaddd-linter]` configuration from the
nearest `pyproject.toml`.
