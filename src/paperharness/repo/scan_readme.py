"""Public API for README command-line extraction."""

from __future__ import annotations

from pathlib import Path

from paperharness.repo.scan import scan_repo


def scan_readme(repo_path: Path) -> list[str]:
    return scan_repo(repo_path).readme_commands
