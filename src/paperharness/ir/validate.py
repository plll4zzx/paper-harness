from __future__ import annotations

from pathlib import Path

from paperharness.ir.io import read_yaml


def validate_output(output_dir: Path) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    ok: list[str] = []

    reprokit_path = output_dir / "reprokit.yaml"
    if reprokit_path.exists():
        ok.append("reprokit.yaml found")
        kit = read_yaml(reprokit_path)
        if kit.experiments:
            ok.append(f"{len(kit.experiments)} experiments found")
        else:
            warnings.append("no experiments found")
        for exp in kit.experiments:
            has_command = any(
                [exp.setup.command, exp.data.command, exp.smoke.command, exp.run.command, exp.evaluate.command]
            )
            if not exp.id:
                errors.append("experiment missing id")
            if exp.status == "mapped" and not has_command:
                errors.append(f"mapped experiment has no command: {exp.id}")
            if not exp.evidence and not exp.risks:
                warnings.append(f"experiment has no evidence or warning: {exp.id}")
            if exp.unmatched_paper_symbols:
                warnings.append(f"unmatched paper symbols for {exp.id}: {', '.join(exp.unmatched_paper_symbols)}")
            if exp.implementation_status in {"partial_candidate", "missing"}:
                warnings.append(f"{exp.id} implementation status: {exp.implementation_status}")
    else:
        errors.append("reprokit.yaml missing")

    required = [
        output_dir / "skill" / "SKILL.md",
        output_dir / "skill" / "scripts" / "repro.py",
        output_dir / "experiment_plan.md",
        output_dir / "report_template.md",
        output_dir / "missing_info.md",
    ]
    for path in required:
        if path.exists():
            ok.append(f"{path.relative_to(output_dir)} found")
        else:
            errors.append(f"{path.relative_to(output_dir)} missing")
    return ok, warnings, errors
