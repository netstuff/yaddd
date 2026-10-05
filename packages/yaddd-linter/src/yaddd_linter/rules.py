"""Violation codes and messages for the yaddd linter."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Violation:
    """A single linter violation."""

    path: str
    line: int
    col: int
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.col}: {self.code} {self.message}"


#: All violation codes emitted by the linter.
ALL_CODES: frozenset[str] = frozenset({"YDDD001", "YDDD002", "YDDD003", "YDDD004", "YDDD005"})


class Rule:
    """Base class for linter rules."""

    def check(self, path: Path, source: str) -> list[Violation]:
        """Return all violations found in the given source file."""
        raise NotImplementedError
