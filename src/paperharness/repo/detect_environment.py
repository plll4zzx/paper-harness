from __future__ import annotations

from pathlib import Path

from paperharness.repo.scan import scan_repo


def detect_environment(repo_path: Path):
    return scan_repo(repo_path).environment
