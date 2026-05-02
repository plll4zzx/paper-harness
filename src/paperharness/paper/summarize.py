from __future__ import annotations

from paperharness.ir.schema import PaperFacts


def summarize_paper(facts: PaperFacts) -> str:
    datasets = ", ".join(facts.datasets) or "unknown datasets"
    metrics = ", ".join(facts.metrics) or "unknown metrics"
    return f"{facts.title or 'Untitled paper'}; datasets={datasets}; metrics={metrics}"
