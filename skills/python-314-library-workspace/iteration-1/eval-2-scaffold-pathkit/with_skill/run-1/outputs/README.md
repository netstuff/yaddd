# pathkit

Small utilities on top of `pathlib` for working with paths. Python 3.14+.

## Usage

```python
from pathlib import Path

from pathkit import ensure_extension

ensure_extension(Path("report"), ".txt")  # PosixPath('report.txt')
```

## Development

```bash
uv sync --all-groups
ruff check . && ruff format --check .
mypy src && pyright src
pytest
```
