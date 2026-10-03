"""Tests for :mod:`pathkit._core`."""

from pathlib import Path

from pathkit import ensure_extension


def test_appends_extension_when_missing() -> None:
    assert ensure_extension(Path("report"), ".txt") == Path("report.txt")


def test_appends_extension_without_leading_dot() -> None:
    assert ensure_extension(Path("report"), "txt") == Path("report.txt")


def test_keeps_path_when_extension_matches() -> None:
    assert ensure_extension(Path("report.txt"), ".txt") == Path("report.txt")


def test_comparison_is_case_insensitive() -> None:
    assert ensure_extension(Path("report.PDF"), ".pdf") == Path("report.PDF")


def test_replaces_different_suffix() -> None:
    assert ensure_extension(Path("archive.tar.gz"), ".zip") == Path("archive.tar.zip")
