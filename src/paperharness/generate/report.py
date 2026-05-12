"""Render ``report_template.md`` (top-level and skill/assets copy)."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment

from paperharness.generate.kit import generate_kit, render_template
from paperharness.ir.schema import ReproKit


def generate_report_template(kit: ReproKit, output_dir: Path, env: Environment) -> None:
    render_template(env, "report_template.md.j2", output_dir / "report_template.md", kit=kit)
    render_template(
        env,
        "report_template.md.j2",
        output_dir / "skill" / "assets" / "report_template.md",
        kit=kit,
    )


__all__ = ["generate_report_template", "generate_kit"]
