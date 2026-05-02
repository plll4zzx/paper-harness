from __future__ import annotations

import re
from pathlib import Path

from paperharness.ir.schema import PaperFacts, PaperResult


DATASETS = ["CIFAR-10", "CIFAR-100", "ImageNet", "MNIST", "COCO", "SQuAD", "GLUE", "WMT", "WikiText"]
METRICS = ["accuracy", "acc", "F1", "BLEU", "ROUGE", "loss", "perplexity", "mAP", "AUC"]
SYMBOL_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_]*(?:_[A-Za-z0-9]+)*|[α-ωΑ-Ω])(?=\s*=)")


def parse_paper(path: Path) -> PaperFacts:
    text = extract_text(path)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else None
    datasets = _find_terms(text, DATASETS)
    metrics = _find_terms(text, METRICS)
    symbols = _extract_symbols(text)
    results = _extract_results(text, datasets, metrics, symbols)
    abstract = _section_after(text, "abstract")
    claims = _claim_sentences(text)
    return PaperFacts(
        title=title,
        abstract=abstract,
        main_claims=claims,
        datasets=datasets,
        metrics=metrics,
        symbols=symbols,
        results=results,
    )


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        import fitz

        with fitz.open(path) as doc:
            return "\n".join(page.get_text() for page in doc)
    raise ValueError(f"Unsupported paper format: {path.suffix}")


def _find_terms(text: str, terms: list[str]) -> list[str]:
    found = []
    for term in terms:
        pattern = re.escape(term)
        if term.replace("-", "").isalnum():
            pattern = rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            found.append(term)
    return found


def _extract_symbols(text: str) -> list[str]:
    stop = {
        "and",
        "for",
        "the",
        "with",
        "using",
        "Table",
        "Figure",
        "We",
        "The",
        "Results",
        "Evaluation",
        "Experiments",
        "Model",
    }
    symbols = {m.group(1) for m in SYMBOL_RE.finditer(text)}
    for match in re.finditer(r"symbols?\s+(.+?)(?:\.|\n)", text, flags=re.IGNORECASE):
        phrase = re.split(r"\s+for\s+|\s+to\s+", match.group(1), maxsplit=1)[0]
        for token in re.split(r"\s*,\s*|\s+and\s+|\s+", phrase):
            token = token.strip(" ,.;:()")
            if token:
                symbols.add(token)
    return sorted(s for s in symbols if s not in stop and len(s) <= 40)


def _extract_results(text: str, datasets: list[str], metrics: list[str], symbols: list[str]) -> list[PaperResult]:
    results: list[PaperResult] = []
    result_lines = []
    for line in text.splitlines():
        lower = line.lower()
        if any(d.lower() in lower for d in datasets) and any(m.lower() in lower for m in metrics):
            result_lines.append(line.strip())
    if not result_lines and (datasets or metrics):
        result_lines = [f"Candidate result for {datasets[0] if datasets else 'unknown dataset'}"]
    for idx, line in enumerate(result_lines, start=1):
        dataset = next((d for d in datasets if d.lower() in line.lower()), datasets[0] if datasets else None)
        metric = next((m for m in metrics if m.lower() in line.lower()), metrics[0] if metrics else None)
        value = _expected_number(line)
        results.append(
            PaperResult(
                id=f"result{idx}",
                label=f"Result {idx}",
                description=line,
                dataset=dataset,
                metric=metric,
                expected_value=value,
                tolerance=1.0 if value is not None else None,
                unit="percent" if metric and metric.lower() in {"accuracy", "acc", "f1"} else None,
                symbols=symbols[:20],
                confidence=0.5 if value is not None else 0.3,
            )
        )
    return results


def _expected_number(text: str) -> float | None:
    percent = re.findall(r"(?<![A-Za-z])(\d+(?:\.\d+)?)\s*(?:%|percent)\b", text, flags=re.IGNORECASE)
    if percent:
        return float(percent[-1])
    if not re.search(r"\b(achieve|achieves|reported|reports|obtains|accuracy of|f1 of|bleu of)\b", text, re.IGNORECASE):
        return None
    numbers = re.findall(r"(?<![A-Za-z0-9.-])(\d+(?:\.\d+)?)(?![A-Za-z0-9.-])", text)
    if not numbers:
        return None
    return float(numbers[-1])


def _section_after(text: str, name: str) -> str | None:
    match = re.search(rf"{name}\s*\n(.+?)(?:\n\s*\n|$)", text, flags=re.IGNORECASE | re.DOTALL)
    return " ".join(match.group(1).split()) if match else None


def _claim_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    keys = ("outperform", "state-of-the-art", "improve", "achieve", "reduce")
    return [s.strip() for s in sentences if any(k in s.lower() for k in keys)][:5]
