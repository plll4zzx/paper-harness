"""Render ``skill/SKILL.md`` — the per-paper agent skill."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment

from paperharness.generate.kit import generate_kit, render_template
from paperharness.ir.schema import ReproKit


def generate_skill(kit: ReproKit, output_dir: Path, env: Environment) -> None:
    render_template(env, "SKILL.md.j2", output_dir / "skill" / "SKILL.md", kit=kit)


__all__ = ["generate_skill", "generate_kit"]
