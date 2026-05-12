"""Group paper results into *experiments* (one experiment per dataset/metric).

A paper typically reports several numbers for the same experiment — e.g.
accuracy and F1 on the same dataset row of a table. Downstream we want one
experiment per ``(dataset, configuration)`` slot, with metrics attached as
multiple results. This module performs that grouping on top of the raw
:func:`extract_results` output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from paperharness.ir.schema import PaperResult
from paperharness.paper.extract_results import extract_results


@dataclass
class PaperExperiment:
    """Logical grouping: one paper experiment with potentially multiple results."""

    id: str
    dataset: str | None
    results: list[PaperResult] = field(default_factory=list)

    @property
    def metrics(self) -> list[str]:
        seen: list[str] = []
        for r in self.results:
            if r.metric and r.metric not in seen:
                seen.append(r.metric)
        return seen


def extract_experiments(
    path: Path,
    extraction: dict | None = None,
    grobid_url: str | None = None,
) -> list[PaperExperiment]:
    results = extract_results(path, extraction=extraction, grobid_url=grobid_url)
    buckets: dict[str, PaperExperiment] = {}
    for result in results:
        key = (result.dataset or "unknown").lower()
        bucket = buckets.setdefault(
            key,
            PaperExperiment(id=f"exp_{key}", dataset=result.dataset),
        )
        bucket.results.append(result)
    return list(buckets.values())
