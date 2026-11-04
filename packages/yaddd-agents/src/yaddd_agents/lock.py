"""Deterministic lock file for generated agent rules."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from yaddd_agents import __version__
from yaddd_agents.model import Project, Resolution


def sha256_text(value: str) -> str:
    """Return the SHA-256 digest of a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_lock(project: Project, resolution: Resolution, outputs: dict[Path, str]) -> str:
    """Build a deterministic ``manifest.lock.json`` payload."""
    packs = [
        {
            "name": pack.name,
            "version": pack.version,
            "manifest_sha256": sha256_file(pack.manifest_path),
        }
        for pack in resolution.packs
    ]
    payload = {
        "schema": 1,
        "generator": {"name": "yaddd-agents", "version": __version__},
        "project": project.pyproject_path.name,
        "packs": packs,
        "outputs": {path.as_posix(): sha256_text(content) for path, content in sorted(outputs.items())},
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
