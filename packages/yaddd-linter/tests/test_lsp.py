"""Tests for yaddd_linter LSP server."""

import textwrap
from pathlib import Path

from lsprotocol.types import (
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    DiagnosticSeverity,
)

from yaddd_linter.lsp import check_document, server


def test_server_features_registered() -> None:
    features: dict = server.lsp.fm.features  # type: ignore[assignment]
    assert TEXT_DOCUMENT_DID_OPEN in features
    assert TEXT_DOCUMENT_DID_CHANGE in features
    assert TEXT_DOCUMENT_DID_SAVE in features
    assert TEXT_DOCUMENT_DID_CLOSE in features


def test_check_document_reports_violation(tmp_path: Path) -> None:
    path = tmp_path / "packages" / "yaddd" / "src" / "yaddd" / "domain" / "order.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("from yaddd.application.commands import CreateOrder\n", encoding="utf-8")

    diagnostics = check_document(f"file://{path}", path.read_text(), path)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "YDDD003"
    assert diagnostic.severity == DiagnosticSeverity.Error
    assert diagnostic.source == "yaddd-linter"
    assert "domain layer imports from application layer" in diagnostic.message


def test_check_document_no_violations(tmp_path: Path) -> None:
    path = tmp_path / "packages" / "yaddd" / "src" / "yaddd" / "application" / "service.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("from yaddd.domain.order import Order\n", encoding="utf-8")

    diagnostics = check_document(f"file://{path}", path.read_text(), path)

    assert diagnostics == []


def test_check_document_honours_config_ignore(tmp_path: Path) -> None:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("from yaddd.application.commands import CreateOrder\n", encoding="utf-8")

    diagnostics = check_document(f"file://{path}", path.read_text(), path)

    assert diagnostics == []


def test_check_document_honours_config_select(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """
            [tool.yaddd-linter]
            select = ["YDDD004"]
            """
        ),
        encoding="utf-8",
    )
    path = tmp_path / "packages" / "yaddd" / "src" / "yaddd" / "domain" / "order.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "from yaddd.application.commands import CreateOrder\nimport sqlalchemy\n",
        encoding="utf-8",
    )

    diagnostics = check_document(f"file://{path}", path.read_text(), path)

    codes = {d.code for d in diagnostics}
    assert codes == {"YDDD004"}
