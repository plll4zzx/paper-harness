from __future__ import annotations

from pathlib import Path

from paperharness.paper.parse import parse_paper


def extract_experiments(path: Path):
    return parse_paper(path).results
