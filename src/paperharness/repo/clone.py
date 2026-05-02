from __future__ import annotations

from pathlib import Path


def clone_or_resolve(repo: str, destination: Path | None = None) -> Path:
    path = Path(repo)
    if path.exists():
        return path.resolve()
    if destination is None:
        raise ValueError("remote cloning is not implemented in the MVP without an explicit destination")
    from git import Repo

    Repo.clone_from(repo, destination)
    return destination.resolve()
