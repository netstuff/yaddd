"""Core path utilities built on :mod:`pathlib`."""

from pathlib import Path

__all__ = ["ensure_extension"]


def ensure_extension(path: Path, extension: str) -> Path:
    """Return *path* with *extension* guaranteed, appending it only if missing.

    The extension may be given with or without a leading dot. Comparison is
    case-insensitive, so ``report.PDF`` is not given a second ``.pdf``.

    Args:
        path: The path to normalize.
        extension: The desired extension, with or without a leading dot.

    Returns:
        The path unchanged if it already ends in the extension, otherwise a
        new path with the extension appended.

    """
    ext = extension if extension.startswith(".") else f".{extension}"
    if ext == ".":
        msg = "extension must not be empty"
        raise ValueError(msg)
    if path.suffix.lower() == ext.lower():
        return path
    return path.with_suffix(ext)
