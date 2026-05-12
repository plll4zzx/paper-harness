"""Repository resolution: accept either a local path or a remote URL.

The README promises ``paperharness build --repo <github-url>`` but historically
that path was unimplemented. This module provides:

- :func:`looks_like_url` to decide whether ``--repo`` needs cloning;
- :func:`resolve_repo` which returns a local :class:`Path`, cloning if needed.

Cloning is shallow (``depth=1``) by default to keep CI snappy and avoid pulling
multi-GB histories of large research repos. Pass ``depth=None`` to disable.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


URL_RE = re.compile(r"^(https?://|git@|ssh://|git://)")


def looks_like_url(value: str) -> bool:
    if URL_RE.match(value):
        return True
    if value.endswith(".git"):
        return True
    if "/" in value and not Path(value).expanduser().exists() and value.count("/") == 1:
        # bare "owner/repo" shorthand
        return True
    return False


def normalize_url(value: str) -> str:
    if URL_RE.match(value) or value.endswith(".git"):
        return value
    if "/" in value and value.count("/") == 1:
        return f"https://github.com/{value}.git"
    return value


def resolve_repo(repo: str, workdir: Path | None = None, depth: int | None = 1) -> Path:
    """Return a local checkout for ``repo``.

    - If ``repo`` is an existing local path, return its resolved absolute form.
    - Otherwise clone it into ``workdir`` (or a tempdir) and return the clone.
    """
    path = Path(repo).expanduser()
    if path.exists():
        return path.resolve()
    if not looks_like_url(repo):
        raise FileNotFoundError(f"--repo is neither an existing path nor a URL-like string: {repo}")
    url = normalize_url(repo)
    target = workdir or Path(tempfile.mkdtemp(prefix="paperharness-repo-"))
    target.mkdir(parents=True, exist_ok=True)
    clone_dir = target / _slug_for_url(url)
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    cmd = ["git", "clone"]
    if depth:
        cmd += ["--depth", str(depth)]
    cmd += [url, str(clone_dir)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("`git` executable not found; install git to clone remote repositories.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git clone failed for {url}: {exc.stderr.strip()}") from exc
    return clone_dir.resolve()


def clone_or_resolve(repo: str, destination: Path | None = None) -> Path:
    """Backwards-compatible alias kept for callers that imported the original name."""
    return resolve_repo(repo, workdir=destination)


def _slug_for_url(url: str) -> str:
    raw = url.rstrip("/").split("/")[-1]
    if raw.endswith(".git"):
        raw = raw[:-4]
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw) or "repo"
