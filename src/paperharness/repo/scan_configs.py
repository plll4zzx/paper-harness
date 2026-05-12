"""Public API for config-file discovery."""

from __future__ import annotations

from pathlib import Path

from paperharness.repo.scan import scan_repo


def scan_configs(repo_path: Path) -> list[str]:
    return scan_repo(repo_path).config_files
