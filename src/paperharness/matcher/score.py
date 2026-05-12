"""Public scoring API for one (dataset, metric, repository) tuple.

The internal :func:`paperharness.matcher.match._score` returns
``(score, evidence, risks)``; downstream callers want a friendlier shape.
"""

from __future__ import annotations

from dataclasses import dataclass

from paperharness.ir.schema import EvidenceSpec, RepoFacts
from paperharness.matcher.match import _score


@dataclass
class MatchScore:
    score: float
    evidence: list[EvidenceSpec]
    risks: list[str]

    @property
    def is_mapped(self) -> bool:
        return self.score >= 0.2

    @property
    def is_complete_candidate(self) -> bool:
        return self.score >= 0.5


def score_match(dataset: str | None, metric: str | None, repo: RepoFacts) -> MatchScore:
    score, evidence, risks = _score(dataset, metric, repo)
    return MatchScore(score=score, evidence=evidence, risks=risks)
