from pathlib import Path

from paperharness.repo.scan import scan_repo


def test_repo_scan_detects_commands_and_symbols() -> None:
    facts = scan_repo(Path("examples/minimal_pytorch/repo"))
    assert "python train.py --config configs/cifar10.yaml" in facts.command_candidates
    assert "python evaluate.py --checkpoint outputs/best.pt" in facts.command_candidates
    assert "main" in facts.code_symbols
    assert "configs/cifar10.yaml" in facts.config_files
