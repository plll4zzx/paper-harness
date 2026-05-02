from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from paperharness.ir.io import write_yaml
from paperharness.ir.schema import ReproKit


def generate_kit(kit: ReproKit, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "skill" / "scripts").mkdir(parents=True, exist_ok=True)
    (output_dir / "skill" / "references").mkdir(parents=True, exist_ok=True)
    (output_dir / "skill" / "assets").mkdir(parents=True, exist_ok=True)
    write_yaml(output_dir / "reprokit.yaml", kit)
    write_yaml(output_dir / "skill" / "reprokit.yaml", kit)

    env = _env()
    _render(env, "SKILL.md.j2", output_dir / "skill" / "SKILL.md", kit=kit)
    _render(env, "repro.py.j2", output_dir / "skill" / "scripts" / "repro.py", kit=kit)
    _write_helper_scripts(output_dir / "skill" / "scripts")
    _render(env, "experiment_plan.md.j2", output_dir / "experiment_plan.md", kit=kit)
    _render(env, "report_template.md.j2", output_dir / "report_template.md", kit=kit)
    _render(env, "missing_info.md.j2", output_dir / "missing_info.md", kit=kit)
    _render(env, "paper_summary.md.j2", output_dir / "skill" / "references" / "paper_summary.md", kit=kit)
    _render(env, "repo_summary.md.j2", output_dir / "skill" / "references" / "repo_summary.md", kit=kit)
    _render(env, "experiment_map.md.j2", output_dir / "skill" / "references" / "experiment_map.md", kit=kit)
    _render(env, "report_template.md.j2", output_dir / "skill" / "assets" / "report_template.md", kit=kit)


def _env() -> Environment:
    template_dir = files("paperharness").joinpath("templates")
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _render(env: Environment, template: str, path: Path, **context: object) -> None:
    path.write_text(env.get_template(template).render(**context), encoding="utf-8")


def _write_helper_scripts(scripts_dir: Path) -> None:
    helpers = {
        "setup_env.py": "setup",
        "smoke_test.py": "smoke",
        "collect_results.py": "collect",
        "write_report.py": "report",
    }
    experiment_helpers = {
        "run_experiment.py": "run",
        "evaluate.py": "evaluate",
    }
    for filename, command in helpers.items():
        (scripts_dir / filename).write_text(_helper_body(command, needs_experiment=False), encoding="utf-8")
    for filename, command in experiment_helpers.items():
        (scripts_dir / filename).write_text(_helper_body(command, needs_experiment=True), encoding="utf-8")


def _helper_body(command: str, needs_experiment: bool) -> str:
    extra = "\n    parser.add_argument('experiment_id')\n" if needs_experiment else ""
    argv = f"[str(Path(__file__).with_name('repro.py')), '{command}', args.experiment_id]" if needs_experiment else f"[str(Path(__file__).with_name('repro.py')), '{command}']"
    return f"""#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
{extra if extra else ''}    args = parser.parse_args()
    raise SystemExit(subprocess.call([sys.executable, *{argv}]))


if __name__ == "__main__":
    main()
"""
