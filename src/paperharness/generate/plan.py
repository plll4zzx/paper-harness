"""Render ``experiment_plan.md`` and ``missing_info.md``.

These two artifacts together tell the agent what to do (the plan) and what is
blocking trust (missing information + low-confidence review items).
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment

from paperharness.generate.kit import generate_kit, render_template
from paperharness.ir.schema import ReproKit
from paperharness.matcher.missing import missing_for_kit


def generate_plan(kit: ReproKit, output_dir: Path, env: Environment) -> None:
    missing_per_experiment = missing_for_kit(kit)
    render_template(env, "experiment_plan.md.j2", output_dir / "experiment_plan.md", kit=kit)
    render_template(
        env,
        "missing_info.md.j2",
        output_dir / "missing_info.md",
        kit=kit,
        missing_per_experiment=missing_per_experiment,
    )


__all__ = ["generate_plan", "generate_kit"]
