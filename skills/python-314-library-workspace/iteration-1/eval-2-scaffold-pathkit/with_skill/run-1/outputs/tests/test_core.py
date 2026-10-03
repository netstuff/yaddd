"""Tests for the public pathkit API, called the way a user would."""

from pathlib import Path

import pytest

from pathkit import ensure_extension


def test_ensure_extension_appends_missing_extension() -> None:
    assert ensure_extension(Path("report"), ".txt") == Path("report.txt")


def test_ensure_extension_accepts_extension_without_dot() -> None:
    assert ensure_extension(Path("report"), "txt") == Path("report.txt")


def test_ensure_extension_keeps_existing_extension() -> None:
    assert ensure_extension(Path("report.txt"), ".txt") == Path("report.txt")


def test_ensure_extension_replaces_wrong_extension() -> None:
    assert ensure_extension(Path("report.md"), ".txt") == Path("report.txt")


def test_ensure_extension_compares_case_insensitively() -> None:
    assert ensure_extension(Path("report.TXT"), ".txt") == Path("report.TXT")


def test_ensure_extension_rejects_empty_extension() -> None:
    with pytest.raises(ValueError, match="extension must not be empty"):
        ensure_extension(Path("report"), "")
