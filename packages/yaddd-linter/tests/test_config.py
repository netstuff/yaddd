"""Tests for yaddd_linter configuration discovery."""

import textwrap
from pathlib import Path

import pytest

from yaddd_linter.config import Config, LayerPolicy, load_config


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


def test_load_config_reads_layers_next_to_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'demo'\nversion = '0.1.0'\n", encoding="utf-8")
    layers_dir = tmp_path / ".yaddd"
    layers_dir.mkdir()
    (layers_dir / "layers.json").write_text(
        textwrap.dedent(
            """
            {
              "schema": 1,
              "layers": {
                "domain": {"imports": ["domain"], "third_party": ["pydantic"]},
                "application": {"imports": ["domain", "application"], "third_party": []}
              }
            }
            """
        ),
        encoding="utf-8",
    )

    config = load_config(pyproject)

    assert config.policy_for("domain") == LayerPolicy(
        imports=frozenset({"domain"}),
        third_party=frozenset({"pydantic"}),
    )
    assert config.policy_for("application") == LayerPolicy(
        imports=frozenset({"domain", "application"}),
        third_party=frozenset(),
    )
    assert config.policy_for("presentation") is None


def test_load_config_explicit_layers_path(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'demo'\nversion = '0.1.0'\n", encoding="utf-8")
    layers = tmp_path / "custom.json"
    layers.write_text(
        '{"schema": 1, "layers": {"domain": {"imports": ["domain"], "third_party": []}}}',
        encoding="utf-8",
    )

    config = load_config(pyproject, layers)

    assert config.policy_for("domain") is not None
