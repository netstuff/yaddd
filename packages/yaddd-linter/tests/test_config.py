"""Tests for yaddd_linter configuration discovery."""

import textwrap
from pathlib import Path

import pytest

from yaddd_linter.config import Config, load_config


def test_load_config_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.toml")
    assert config == Config(select=frozenset(), ignore=frozenset(), exclude=())


def test_load_config_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """
            [tool.yaddd-linter]
            select = ["YDDD001", "YDDD003"]
            ignore = ["YDDD004"]
            exclude = ["**/migrations/**"]
            """
        ),
        encoding="utf-8",
    )
    config = load_config(pyproject)
    assert config.select == {"YDDD001", "YDDD003"}
    assert config.ignore == {"YDDD004"}
    assert config.exclude == ("**/migrations/**",)


def test_load_config_unknown_code_raises(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """
            [tool.yaddd-linter]
            select = ["YDDD001", "UNKNOWN"]
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unknown yaddd-linter rule codes"):
        load_config(pyproject)


def test_config_is_enabled() -> None:
    config = Config(select=frozenset({"YDDD001", "YDDD002"}), ignore=frozenset({"YDDD002"}), exclude=())
    assert config.is_enabled("YDDD001") is True
    assert config.is_enabled("YDDD002") is False
    assert config.is_enabled("YDDD003") is False


def test_config_ignore_without_select() -> None:
    config = Config(select=frozenset(), ignore=frozenset({"YDDD001"}), exclude=())
    assert config.is_enabled("YDDD001") is False
    assert config.is_enabled("YDDD002") is True
