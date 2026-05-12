from __future__ import annotations

from pathlib import Path

from paperharness.repo.clone import looks_like_url, normalize_url, resolve_repo


def test_looks_like_url_recognises_common_forms() -> None:
    assert looks_like_url("https://github.com/foo/bar")
    assert looks_like_url("git@github.com:foo/bar.git")
    assert looks_like_url("foo/bar")
    assert looks_like_url("ssh://git@example.com/foo/bar.git")
    assert not looks_like_url("examples/minimal_pytorch/repo")
    assert not looks_like_url("./some/path")


def test_normalize_url_expands_shorthand() -> None:
    assert normalize_url("foo/bar") == "https://github.com/foo/bar.git"
    assert normalize_url("https://example.com/foo.git") == "https://example.com/foo.git"


def test_resolve_repo_returns_local_path_unchanged(tmp_path: Path) -> None:
    local = tmp_path / "repo"
    local.mkdir()
    assert resolve_repo(str(local)) == local.resolve()
