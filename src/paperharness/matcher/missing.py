"""Per-experiment missing-information enumeration.

`build_experiments` produces a *kit-wide* missing list. This helper produces a
*per-experiment* list which the kit's report uses to explain blockers next to
each experiment ID.
"""

from __future__ import annotations

from paperharness.ir.schema import ExperimentSpec, ReproKit


def missing_for_experiment(experiment: ExperimentSpec) -> list[str]:
    missing: list[str] = []
    if not experiment.run.command:
        missing.append("run command missing")
    if not experiment.evaluate.command:
        missing.append("evaluation command missing")
    if not experiment.setup.command:
        missing.append("setup command missing")
    if not experiment.data.command:
        missing.append("data preparation command missing")
    if experiment.implementation_status == "missing":
        missing.append("repository does not appear to implement this experiment")
    if experiment.implementation_status == "partial_candidate":
        missing.append("repository appears to implement only part of this experiment")
    missing.extend(f"unmatched paper symbol: {s}" for s in experiment.unmatched_paper_symbols)
    return missing


def missing_for_kit(kit: ReproKit) -> dict[str, list[str]]:
    """Return ``{experiment_id: [missing items...]}`` for every experiment."""
    return {exp.id: missing_for_experiment(exp) for exp in kit.experiments}
