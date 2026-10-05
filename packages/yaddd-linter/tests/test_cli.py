"""Tests for yaddd_linter CLI."""

import json
import sys
import textwrap
from pathlib import Path

import pytest

from yaddd_linter.cli import main


def _write_file(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_cli_no_paths_prints_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "required: paths" in captured.err


def test_cli_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "packages" / "yaddd" / "src" / "yaddd" / "domain" / "order.py"
    _write_file(
        path,
        "from yaddd.application.commands import CreateOrder\n",
    )
    exit_code = main([str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "YDDD003" in captured.out
    assert "domain layer imports from application layer" in captured.out


def test_cli_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "packages" / "yaddd" / "src" / "yaddd" / "domain" / "order.py"
    _write_file(
        path,
        "from yaddd.application.commands import CreateOrder\n",
    )
    exit_code = main(["--format", "json", str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    payload = json.loads(captured.out)
    assert len(payload) == 1
    assert payload[0]["code"] == "YDDD003"


def test_cli_select_filter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "packages" / "yaddd" / "src" / "yaddd" / "domain" / "order.py"
    _write_file(
        path,
        "from yaddd.application.commands import CreateOrder\nimport sqlalchemy\n",
    )
    exit_code = main(["--select", "YDDD004", "--format", "json", str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    payload = json.loads(captured.out)
    codes = {item["code"] for item in payload}
    assert codes == {"YDDD004"}


def test_cli_ignore_filter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "packages" / "yaddd" / "src" / "yaddd" / "domain" / "order.py"
    _write_file(
        path,
        "from yaddd.application.commands import CreateOrder\n",
    )
    exit_code = main(["--ignore", "YDDD003", str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_cli_stdin(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    class _Stdin:
        def read(self, _size: int = -1) -> str:
            return "from yaddd.application.commands import CreateOrder\n"

    monkeypatch.setattr(sys, "stdin", _Stdin())
    exit_code = main(
        [
            "--stdin-filename",
            "packages/yaddd/src/yaddd/domain/order.py",
            "-",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "YDDD003" in captured.out


def test_cli_config_from_pyproject(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """
            [tool.yaddd-linter]
            ignore = ["YDDD003"]
            """
        ),
        encoding="utf-8",
    )
    path = tmp_path / "packages" / "yaddd" / "src" / "yaddd" / "domain" / "order.py"
    _write_file(
        path,
        "from yaddd.application.commands import CreateOrder\n",
    )
    exit_code = main(["--config", str(pyproject), str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""


def test_cli_unknown_code_returns_error(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--select", "YDDD999", "."])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "Unknown yaddd-linter rule codes" in captured.err
