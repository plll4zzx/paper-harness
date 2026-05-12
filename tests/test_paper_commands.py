from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from paperharness.cli import app
from paperharness.ir.schema import ExperimentSpec, RepoEnvironment, RepoFacts
from paperharness.paper import llm_extract


def test_attach_reproduction_commands_routes_phases() -> None:
    repo = RepoFacts(environment=RepoEnvironment())
    exps = [
        ExperimentSpec(id="r1_cifar", paper_result_id="r1", title="r1", implementation_status="missing"),
        ExperimentSpec(id="r2_cifar", paper_result_id="r2", title="r2"),
    ]
    extraction = {
        "reproduction_commands": [
            {"phase": "setup", "command": "sh install.sh", "source_span": "Install all required dependencies by running sh install.sh."},
            {"phase": "run", "command": "python test_rand_sh.py --wm_name KGW", "applies_to": ["r1"], "source_span": "[Execution] The following command..."},
            {"phase": "evaluate", "command": "python eval.py", "source_span": "Evaluation step."},
        ]
    }
    log = llm_extract.attach_reproduction_commands(exps, repo, extraction)
    assert exps[0].setup.command == "sh install.sh"
    assert exps[0].setup.source == "paper"
    assert exps[0].run.command.startswith("python test_rand_sh.py")
    assert exps[0].run.source == "paper"
    assert exps[0].implementation_status == "complete_candidate"
    assert exps[0].status == "mapped"
    assert exps[0].confidence >= 0.6
    # applies_to=["r1"] should NOT attach run command to r2_cifar
    assert exps[1].run.command is None
    # But setup with no applies_to applies to both
    assert exps[1].setup.command == "sh install.sh"
    # repo install_commands also picks up setup command
    assert "sh install.sh" in repo.environment.install_commands
    assert any("r1_cifar.setup" in line for line in log)


def test_build_uses_paper_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    extraction = {
        "title": "T",
        "datasets": ["CIFAR-10"],
        "metrics": ["accuracy"],
        "results": [{
            "id": "r1",
            "label": "r1",
            "dataset": "CIFAR-10",
            "metric": "accuracy",
            "confidence": 0.9,
            "config": {"wm_name": "KGW", "max_edit_rate": 0.1},
            "source_span": "We report 94.2.",
        }],
        "reproduction_commands": [
            {"phase": "run", "command": "python train.py --foo bar --baz qux", "source_span": "see Appendix B"},
        ],
    }
    extraction_path = tmp_path / "x.json"
    extraction_path.write_text(json.dumps(extraction), encoding="utf-8")
    out = tmp_path / "out"
    result = runner.invoke(app, [
        "build",
        "--paper", "examples/minimal_pytorch/paper.txt",
        "--repo", "examples/minimal_pytorch/repo",
        "--out", str(out),
        "--extraction", str(extraction_path),
    ])
    assert result.exit_code == 0, result.output
    kit = yaml.safe_load((out / "reprokit.yaml").read_text(encoding="utf-8"))
    exp = kit["experiments"][0]
    assert exp["run"]["command"].startswith("python train.py --foo bar")
    assert exp["run"]["source"] == "paper"
    assert exp["config"] == {"wm_name": "KGW", "max_edit_rate": 0.1}
    assert "wm_name=KGW" not in str(exp["unmatched_paper_symbols"])


def test_entrypoint_glob_finds_test_prefixed_scripts(tmp_path: Path) -> None:
    from paperharness.repo.scan import scan_repo

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "test_rand_sh.py").write_text("import argparse\np=argparse.ArgumentParser()\np.add_argument('--wm_name')\n", encoding="utf-8")
    (repo / "collect_wm_text.py").write_text("import argparse\np=argparse.ArgumentParser()\np.add_argument('--device')\n", encoding="utf-8")
    (repo / "train_ref_detector.py").write_text("import argparse\np=argparse.ArgumentParser()\np.add_argument('--num_epochs')\n", encoding="utf-8")
    facts = scan_repo(repo)
    assert any("test_rand_sh.py" in c for c in facts.entrypoints["evaluate"])
    assert any("collect_wm_text.py" in c for c in facts.entrypoints["data"])
    assert any("train_ref_detector.py" in c for c in facts.entrypoints["train"])
    # argparse flags must survive the hint filter
    assert "wm_name" in facts.code_symbols
    assert "device" in facts.code_symbols
    assert "num_epochs" in facts.code_symbols


def test_dataset_name_with_parens_matches_tokens() -> None:
    from paperharness.matcher.match import _name_appears_in

    assert _name_appears_in("C4 (RealNewsLike subset)", "python train.py --dataset c4/realnewslike")
    assert _name_appears_in("CIFAR-10", "configs/cifar10.yaml")
    assert not _name_appears_in("CIFAR-10", "configs/imagenet.yaml")


def test_extraction_separates_symbols_from_config(tmp_path: Path) -> None:
    runner = CliRunner()
    extraction = {
        "title": "T",
        "datasets": ["d"],
        "metrics": ["m"],
        "symbols": ["alpha", "lambda"],
        "results": [{
            "id": "r1",
            "label": "r1",
            "dataset": "d",
            "metric": "m",
            "confidence": 0.9,
            "symbols": ["alpha"],
            "config": {"alpha": 0.5, "lambda": 0.01},
            "source_span": "We use alpha=0.5.",
        }],
    }
    extraction_path = tmp_path / "x.json"
    extraction_path.write_text(json.dumps(extraction), encoding="utf-8")
    out = tmp_path / "out"
    result = runner.invoke(app, [
        "build",
        "--paper", "examples/minimal_pytorch/paper.txt",
        "--repo", "examples/minimal_pytorch/repo",
        "--out", str(out),
        "--extraction", str(extraction_path),
    ])
    assert result.exit_code == 0, result.output
    kit = yaml.safe_load((out / "reprokit.yaml").read_text(encoding="utf-8"))
    exp = kit["experiments"][0]
    assert exp["config"] == {"alpha": 0.5, "lambda": 0.01}


def test_hardware_propagates_from_extraction(tmp_path: Path) -> None:
    runner = CliRunner()
    extraction = {
        "title": "T",
        "datasets": ["d"],
        "metrics": ["m"],
        "results": [{"id": "r1", "label": "r1", "dataset": "d", "metric": "m", "confidence": 0.8}],
        "hardware": {"gpu_required": True, "min_gpu_memory_gb": 10.0, "notes": "NVIDIA recommended"},
    }
    extraction_path = tmp_path / "x.json"
    extraction_path.write_text(json.dumps(extraction), encoding="utf-8")
    out = tmp_path / "out"
    result = runner.invoke(app, [
        "build",
        "--paper", "examples/minimal_pytorch/paper.txt",
        "--repo", "examples/minimal_pytorch/repo",
        "--out", str(out),
        "--extraction", str(extraction_path),
    ])
    assert result.exit_code == 0, result.output
    summary = (out / "skill" / "references" / "paper_summary.md").read_text(encoding="utf-8")
    assert "Hardware requirements" in summary
    assert "10" in summary
