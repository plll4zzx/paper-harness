from __future__ import annotations

from paperharness.ir.schema import RepoFacts
from paperharness.matcher.match import _score


def score_match(dataset: str | None, metric: str | None, repo: RepoFacts):
    return _score(dataset, metric, repo)
