"""Top-level orchestrator: render every artifact that a reproduction kit needs.

Each ``generate.*`` submodule owns one artifact:

- :mod:`paperharness.generate.skill` — ``skill/SKILL.md``
- :mod:`paperharness.generate.cli_wrapper` — ``skill/scripts/repro.py`` + helper wrappers
- :mod:`paperharness.generate.plan` — ``experiment_plan.md``
- :mod:`paperharness.generate.report` — ``report_template.md`` (+ skill/assets copy)
- :mod:`paperharness.generate.references` — ``skill/references/*``

This module composes them so callers only need to import :func:`generate_kit`.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from paperharness.ir.io import write_yaml
from paperharness.ir.schema import ReproKit


def jinja_env() -> Environment:
    template_dir = files("paperharness").joinpath("templates")
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(env: Environment, template: str, path: Path, **context: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(env.get_template(template).render(**context), encoding="utf-8")


def generate_kit(kit: ReproKit, output_dir: Path) -> None:
    from paperharness.generate import cli_wrapper, plan, references, report, skill

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "skill" / "scripts").mkdir(parents=True, exist_ok=True)
    (output_dir / "skill" / "references").mkdir(parents=True, exist_ok=True)
    (output_dir / "skill" / "assets").mkdir(parents=True, exist_ok=True)
    write_yaml(output_dir / "reprokit.yaml", kit)
    write_yaml(output_dir / "skill" / "reprokit.yaml", kit)

    env = jinja_env()
    skill.generate_skill(kit, output_dir, env)
    cli_wrapper.generate_cli(kit, output_dir, env)
    plan.generate_plan(kit, output_dir, env)
    report.generate_report_template(kit, output_dir, env)
    references.generate_references(kit, output_dir, env)
