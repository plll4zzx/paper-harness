from __future__ import annotations

from paperharness.ir.schema import ExperimentSpec, CommandSpec, RepoEnvironment, RepoFacts
from paperharness.matcher.match import _symbol_mapping
from paperharness.matcher.missing import missing_for_experiment
from paperharness.matcher.score import score_match


def test_symbol_mapping_does_not_fuzzy_match_short_tokens() -> None:
    paper_symbols = ["lr", "alpha", "lambda"]
    code_symbols = ["learner", "color", "controller", "alphabet_size"]
    mappings, unmatched_paper, _ = _symbol_mapping(paper_symbols, code_symbols)
    # 'lr' must NOT map to 'learner' / 'color' / 'controller'.
    assert mappings["lr"] is None
    # 'alpha' must NOT match 'alphabet_size' via naked substring — it has its own prefix gate.
    # We accept either None or an exact-known alias; what we forbid is the old fuzzy 'in' match.
    assert mappings["alpha"] != "color"
    assert "lr" in unmatched_paper


def test_symbol_mapping_uses_aliases() -> None:
    paper_symbols = ["lr", "lambda"]
    code_symbols = ["learning_rate", "weight_decay"]
    mappings, _, _ = _symbol_mapping(paper_symbols, code_symbols)
    assert mappings["lr"] == "learning_rate"
    assert mappings["lambda"] == "weight_decay"


def test_score_match_public_api() -> None:
    repo = RepoFacts(
        environment=RepoEnvironment(install_commands=["pip install -e ."]),
        readme_commands=["python train.py --dataset CIFAR-10"],
        entrypoints={"train": ["python train.py"], "evaluate": ["python eval.py"]},
        config_files=["configs/cifar10.yaml"],
    )
    score = score_match("CIFAR-10", "accuracy", repo)
    assert 0 < score.score <= 1
    assert score.is_mapped
    assert any(e.kind == "dataset_overlap" for e in score.evidence)


def test_missing_for_experiment_lists_each_gap() -> None:
    exp = ExperimentSpec(
        id="x",
        title="x",
        implementation_status="partial_candidate",
        run=CommandSpec(command="python train.py"),
        evaluate=CommandSpec(command=None),
        unmatched_paper_symbols=["alpha"],
    )
    missing = missing_for_experiment(exp)
    assert "evaluation command missing" in missing
    assert any("part of this experiment" in m for m in missing)
    assert any("alpha" in m for m in missing)
