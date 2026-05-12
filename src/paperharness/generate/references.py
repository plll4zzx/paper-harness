"""Render the ``skill/references/`` directory.

This writes ``paper_summary.md`` (via :func:`summarize_paper_markdown` — richer
than the bare Jinja template), ``repo_summary.md``, and ``experiment_map.md``.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment

from paperharness.generate.kit import generate_kit, render_template
from paperharness.ir.schema import ReproKit
from paperharness.paper.summarize import summarize_paper_markdown


def generate_references(kit: ReproKit, output_dir: Path, env: Environment) -> None:
    refs = output_dir / "skill" / "references"
    refs.mkdir(parents=True, exist_ok=True)
    (refs / "paper_summary.md").write_text(summarize_paper_markdown(kit.paper), encoding="utf-8")
    render_template(env, "repo_summary.md.j2", refs / "repo_summary.md", kit=kit)
    render_template(env, "experiment_map.md.j2", refs / "experiment_map.md", kit=kit)


__all__ = ["generate_references", "generate_kit"]
