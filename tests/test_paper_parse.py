from pathlib import Path

from paperharness.paper.parse import parse_paper


def test_paper_parse_detects_result_terms_and_symbols() -> None:
    facts = parse_paper(Path("examples/minimal_pytorch/paper.txt"))
    assert facts.title == "Minimal CIFAR Paper"
    assert "CIFAR-10" in facts.datasets
    assert "accuracy" in [m.lower() for m in facts.metrics]
    assert facts.results
    assert "alpha" in facts.symbols
