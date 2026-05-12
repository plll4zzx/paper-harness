from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from paperharness.cli import app
from paperharness.paper import llm_extract


def test_extract_text_emits_prompt_and_schema(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "extract"
    result = runner.invoke(
        app,
        ["extract-text", "examples/minimal_pytorch/paper.txt", "--out", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert (out / "paper.md").exists()
    prompt = (out / "extraction_prompt.md").read_text(encoding="utf-8")
    assert "PaperHarness" in prompt
    assert "source_span" in prompt
    schema = json.loads((out / "extraction_schema.json").read_text(encoding="utf-8"))
    assert "results" in schema["properties"]


def test_build_with_extraction_uses_llm_facts(tmp_path: Path) -> None:
    runner = CliRunner()
    extraction = {
        "title": "Hand-Crafted Title",
        "authors": ["Ada Lovelace"],
        "abstract": "Short abstract.",
        "datasets": ["CIFAR-10"],
        "metrics": ["accuracy"],
        "symbols": ["alpha", "lambda"],
        "main_claims": ["We achieve 94.2% on CIFAR-10."],
        "results": [
            {
                "id": "cifar10_acc",
                "label": "CIFAR-10 accuracy",
                "description": "Table 1 reports CIFAR-10 accuracy.",
                "dataset": "CIFAR-10",
                "metric": "accuracy",
                "expected_value": 94.2,
                "tolerance": 0.5,
                "unit": "percent",
                "symbols": ["alpha"],
                "confidence": 0.9,
                "source_span": "Table 1 reports CIFAR-10 accuracy of 94.2 percent",
            },
            {
                "id": "speculative",
                "label": "Speculative claim",
                "dataset": "CIFAR-10",
                "metric": "accuracy",
                "confidence": 0.3,
                "source_span": "implied",
            },
        ],
    }
    extraction_path = tmp_path / "extraction.json"
    extraction_path.write_text(json.dumps(extraction), encoding="utf-8")
    out = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "build",
            "--paper", "examples/minimal_pytorch/paper.txt",
            "--repo", "examples/minimal_pytorch/repo",
            "--out", str(out),
            "--extraction", str(extraction_path),
        ],
    )
    assert result.exit_code == 0, result.output
    kit = yaml.safe_load((out / "reprokit.yaml").read_text(encoding="utf-8"))
    paper = kit["paper"]
    assert paper["title"] == "Hand-Crafted Title"
    assert paper["extraction_method"] == "llm"
    assert paper["results"][0]["source_span"].startswith("Table 1")
    assert paper["results"][0]["confidence"] == 0.9
    low_conf = [r for r in kit["review_required"] if r["issue_type"] == "low_confidence_paper_result"]
    assert any(r["experiment_id"] == "speculative" for r in low_conf)


def test_regex_fallback_no_longer_fabricates_results(tmp_path: Path) -> None:
    paper = tmp_path / "paper.txt"
    paper.write_text(
        "Survey of Things\n\nAbstract\nWe survey CIFAR-10 work. No accuracy numbers reported.\n",
        encoding="utf-8",
    )
    from paperharness.paper.parse import parse_paper

    facts = parse_paper(paper)
    assert facts.extraction_method == "regex"
    assert all(r.source_span != "Candidate result for CIFAR-10" for r in facts.results)


def test_review_items_threshold() -> None:
    from paperharness.ir.schema import PaperFacts, PaperResult

    facts = PaperFacts(
        extraction_method="llm",
        results=[
            PaperResult(id="a", label="A", confidence=0.9),
            PaperResult(id="b", label="B", confidence=0.4),
        ],
    )
    items = llm_extract.review_items_from_facts(facts)
    assert [i.experiment_id for i in items] == ["b"]
