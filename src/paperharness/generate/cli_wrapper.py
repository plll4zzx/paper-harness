"""Render ``skill/scripts/repro.py`` and the small named-entrypoint wrappers.

The wrappers (``setup_env.py``, ``smoke_test.py``, ``run_experiment.py``,
``evaluate.py``, ``collect_results.py``, ``write_report.py``) exist so an agent
that prefers a fixed-filename convention has a stable target. Each is a
one-line shim that forwards ``argv`` to ``repro.py <command>``.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment

from paperharness.generate.kit import generate_kit, render_template
from paperharness.ir.schema import ReproKit


WRAPPER_COMMANDS: dict[str, tuple[str, bool]] = {
    "setup_env.py": ("setup", False),
    "smoke_test.py": ("smoke", False),
    "collect_results.py": ("collect", False),
    "write_report.py": ("report", False),
    "run_experiment.py": ("run", True),
    "evaluate.py": ("evaluate", True),
}


def generate_cli(kit: ReproKit, output_dir: Path, env: Environment) -> None:
    scripts_dir = output_dir / "skill" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    render_template(env, "repro.py.j2", scripts_dir / "repro.py", kit=kit)
    for filename, (command, needs_experiment) in WRAPPER_COMMANDS.items():
        (scripts_dir / filename).write_text(_helper_body(command, needs_experiment), encoding="utf-8")


def _helper_body(command: str, needs_experiment: bool) -> str:
    extra = "\n    parser.add_argument('experiment_id')\n" if needs_experiment else ""
    argv = (
        f"[str(Path(__file__).with_name('repro.py')), '{command}', args.experiment_id]"
        if needs_experiment
        else f"[str(Path(__file__).with_name('repro.py')), '{command}']"
    )
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


__all__ = ["generate_cli", "generate_kit", "WRAPPER_COMMANDS"]
