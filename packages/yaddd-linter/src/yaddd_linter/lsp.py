"""LSP server for yaddd-linter."""
# pyright: reportUnknownMemberType=false

from __future__ import annotations

import logging
import sys
from pathlib import Path

from lsprotocol.types import (
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    Position,
    Range,
)
from pygls.server import LanguageServer

from yaddd_linter import __version__
from yaddd_linter.checker import AggregateMutationChecker, LayerIsolationChecker, collect_aggregate_names
from yaddd_linter.config import load_config_for_path
from yaddd_linter.rules import Violation

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
logger = logging.getLogger(__name__)

server = LanguageServer("yaddd-linter", __version__)


def _violation_to_diagnostic(violation: Violation) -> Diagnostic:
    """Convert a linter violation to an LSP diagnostic."""
    line = max(0, violation.line - 1)
    col = max(0, violation.col)
    return Diagnostic(
        range=Range(
            start=Position(line=line, character=col),
            end=Position(line=line, character=col),
        ),
        message=violation.message,
        severity=DiagnosticSeverity.Error,
        code=violation.code,
        source="yaddd-linter",
    )


def check_document(uri: str, source: str, path: Path) -> list[Diagnostic]:
    """Run yaddd-linter rules against a single in-memory document."""
    try:
        config = load_config_for_path(path)
        enabled_codes = config.select if config.select else None
    except ValueError as exc:
        logger.warning("Invalid yaddd-linter config for %s: %s", path, exc)
        return []

    aggregates = collect_aggregate_names([path])
    rules = [
        LayerIsolationChecker(),
        AggregateMutationChecker(aggregates),
    ]

    diagnostics: list[Diagnostic] = []
    for rule in rules:
        for violation in rule.check(path, source):
            if enabled_codes is not None and violation.code not in enabled_codes:
                continue
            if violation.code in config.ignore:
                continue
            diagnostics.append(_violation_to_diagnostic(violation))
    return diagnostics


@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(params: DidOpenTextDocumentParams) -> None:
    """Lint a document when it is opened."""
    text_doc = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = check_document(
        text_doc.uri,
        text_doc.source,
        Path(text_doc.path),
    )
    server.publish_diagnostics(text_doc.uri, diagnostics)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: DidChangeTextDocumentParams) -> None:
    """Lint a document when its content changes."""
    text_doc = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = check_document(
        text_doc.uri,
        text_doc.source,
        Path(text_doc.path),
    )
    server.publish_diagnostics(text_doc.uri, diagnostics)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(params: DidSaveTextDocumentParams) -> None:
    """Lint a document when it is saved."""
    text_doc = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = check_document(
        text_doc.uri,
        text_doc.source,
        Path(text_doc.path),
    )
    server.publish_diagnostics(text_doc.uri, diagnostics)


@server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: DidCloseTextDocumentParams) -> None:
    """Clear diagnostics when a document is closed."""
    server.publish_diagnostics(params.text_document.uri, [])


def main() -> None:
    """Start the LSP server over stdio."""
    server.start_io()


if __name__ == "__main__":
    main()
