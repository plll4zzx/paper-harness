"""Public API for environment/dependency detection."""

from __future__ import annotations

from pathlib import Path

from paperharness.ir.schema import RepoEnvironment
from paperharness.repo.scan import scan_repo


def detect_environment(repo_path: Path) -> RepoEnvironment:
    return scan_repo(repo_path).environment
