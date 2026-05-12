"""Public API for repository entrypoint detection.

Returns the ``entrypoints`` dict produced by the full scan
(:func:`paperharness.repo.scan.scan_repo`) without forcing callers to depend on
the broader :class:`RepoFacts` model.
"""

from __future__ import annotations

from pathlib import Path

from paperharness.repo.scan import scan_repo


def detect_entrypoints(repo_path: Path) -> dict[str, list[str]]:
    return scan_repo(repo_path).entrypoints
