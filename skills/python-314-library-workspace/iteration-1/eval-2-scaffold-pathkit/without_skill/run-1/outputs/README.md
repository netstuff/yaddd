# pathkit

Small utilities on top of [`pathlib`](https://docs.python.org/3/library/pathlib.html)
for working with filesystem paths. Requires **Python 3.14+**. Fully typed
(ships `py.typed`).

## Install

```bash
pip install pathkit
```

## Usage

```python
from pathlib import Path

from pathkit import ensure_extension

ensure_extension(Path("report"), ".txt")   # PosixPath('report.txt')
ensure_extension(Path("report.PDF"), ".pdf")  # PosixPath('report.PDF') — no double suffix
```

## Development

```bash
# install dev dependencies (uv or pip)
uv sync                      # or: pip install -e '.[dev]' with pip-compatible extras

# run the checks
ruff check .
mypy
pyright
pytest
```
