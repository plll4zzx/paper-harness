from __future__ import annotations

from paperharness.ir.schema import ExperimentSpec


def missing_for_experiment(experiment: ExperimentSpec) -> list[str]:
    missing: list[str] = []
    if not experiment.run.command:
        missing.append("run command missing")
    if not experiment.evaluate.command:
        missing.append("evaluation command missing")
    missing.extend(f"unmatched paper symbol: {s}" for s in experiment.unmatched_paper_symbols)
    return missing
