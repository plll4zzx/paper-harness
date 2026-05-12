from __future__ import annotations

from pathlib import Path

from paperharness.ir.schema import PaperFacts, PaperResult
from paperharness.paper.extract_experiments import extract_experiments
from paperharness.paper.summarize import summarize_paper_markdown


def test_summarize_paper_markdown_has_sections() -> None:
    facts = PaperFacts(
        title="Hello",
        authors=["Ada"],
        abstract="Short.",
        datasets=["CIFAR-10"],
        metrics=["accuracy"],
        symbols=["alpha"],
        main_claims=["We achieve 94.2%."],
        results=[
            PaperResult(
                id="r1",
                label="r1",
                dataset="CIFAR-10",
                metric="accuracy",
                expected_value=94.2,
                unit="percent",
                confidence=0.8,
                source_span="94.2 percent",
            )
        ],
        extraction_method="llm",
        source_format="markdown",
    )
    md = summarize_paper_markdown(facts)
    assert "# Hello" in md
    assert "**Authors:**" in md
    assert "## Reported results" in md
    assert "94.2" in md
    assert "extraction: llm" in md


def test_extract_experiments_groups_by_dataset() -> None:
    experiments = extract_experiments(Path("examples/minimal_pytorch/paper.txt"))
    assert experiments
    dataset_keys = [e.dataset for e in experiments]
    assert any("CIFAR" in (d or "") for d in dataset_keys)
