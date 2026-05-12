"""Return the list of quantitative results extracted from a paper.

A *result* is a single number the paper reports (a table cell, a figure label,
or a sentence such as "we achieve 94.2% on CIFAR-10"). It is the unit that
:class:`paperharness.ir.schema.PaperResult` represents and is what
``build_experiments`` consumes to plan experiment specs.
"""

from __future__ import annotations

from pathlib import Path

from paperharness.ir.schema import PaperResult
from paperharness.paper.parse import parse_paper


def extract_results(
    path: Path,
    extraction: dict | None = None,
    grobid_url: str | None = None,
) -> list[PaperResult]:
    return parse_paper(path, extraction=extraction, grobid_url=grobid_url).results
