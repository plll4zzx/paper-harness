from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperharness.ir.schema import HardwareSpec, PaperFacts, PaperResult
from paperharness.paper import grobid_backend, marker_backend


DATASETS = ["CIFAR-10", "CIFAR-100", "ImageNet", "MNIST", "COCO", "SQuAD", "GLUE", "WMT", "WikiText"]
METRICS = ["accuracy", "acc", "F1", "BLEU", "ROUGE", "loss", "perplexity", "mAP", "AUC"]
SYMBOL_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_]*(?:_[A-Za-z0-9]+)*|[α-ωΑ-Ω])(?=\s*=)")


@dataclass
class PaperSource:
    text: str
    source_format: str
    used_marker: bool
    grobid: grobid_backend.GrobidSections | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source_format": self.source_format,
            "used_marker": self.used_marker,
            "grobid": self.grobid.to_dict() if self.grobid else None,
        }


def parse_paper(
    path: Path,
    extraction: dict | None = None,
    grobid_url: str | None = None,
) -> PaperFacts:
    source = load_source(path, grobid_url=grobid_url)
    if extraction is not None:
        facts = _facts_from_extraction(extraction, source)
    else:
        facts = _regex_extract(source)
    return facts


def load_source(path: Path, grobid_url: str | None = None) -> PaperSource:
    suffix = path.suffix.lower()
    if suffix in {".txt"}:
        return PaperSource(text=path.read_text(encoding="utf-8", errors="ignore"), source_format="text", used_marker=False)
    if suffix == ".md":
        return PaperSource(text=path.read_text(encoding="utf-8", errors="ignore"), source_format="markdown", used_marker=False)
    if suffix == ".pdf":
        marker_text = _try_marker(path)
        grobid_sections = grobid_backend.extract_sections(path, grobid_url) if path.exists() else None
        if marker_text is not None:
            return PaperSource(text=marker_text, source_format="markdown", used_marker=True, grobid=grobid_sections)
        return PaperSource(text=_fitz_extract(path), source_format="pdf", used_marker=False, grobid=grobid_sections)
    raise ValueError(f"Unsupported paper format: {path.suffix}")


def extract_text(path: Path) -> str:
    return load_source(path).text


def _try_marker(path: Path) -> str | None:
    if not marker_backend.is_available():
        return None
    try:
        return marker_backend.pdf_to_markdown(path)
    except marker_backend.MarkerUnavailable:
        return None
    except Exception:
        return None


def _fitz_extract(path: Path) -> str:
    import fitz

    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def _regex_extract(source: PaperSource) -> PaperFacts:
    text = source.text
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = source.grobid.title if source.grobid and source.grobid.title else (lines[0] if lines else None)
    abstract = (
        source.grobid.abstract if source.grobid and source.grobid.abstract else _section_after(text, "abstract")
    )
    authors = list(source.grobid.authors) if source.grobid else []
    datasets = _find_terms(text, DATASETS)
    metrics = _find_terms(text, METRICS)
    symbols = _extract_symbols(text)
    results = _extract_results(text, datasets, metrics, symbols)
    claims = _claim_sentences(text)
    return PaperFacts(
        title=title,
        authors=authors,
        abstract=abstract,
        main_claims=claims,
        datasets=datasets,
        metrics=metrics,
        symbols=symbols,
        results=results,
        extraction_method="marker+regex" if source.used_marker else "regex",
        source_format=_normalize_format(source.source_format),
    )


def _facts_from_extraction(extraction: dict, source: PaperSource) -> PaperFacts:
    raw_results = extraction.get("results") or []
    results: list[PaperResult] = []
    for idx, item in enumerate(raw_results, start=1):
        if not isinstance(item, dict):
            continue
        rid = str(item.get("id") or f"result{idx}")
        label = str(item.get("label") or f"Result {idx}")
        cfg = item.get("config") or {}
        if not isinstance(cfg, dict):
            cfg = {}
        results.append(
            PaperResult(
                id=rid,
                label=label,
                description=item.get("description"),
                dataset=item.get("dataset"),
                metric=item.get("metric"),
                expected_value=item.get("expected_value"),
                tolerance=item.get("tolerance"),
                unit=item.get("unit"),
                symbols=_as_str_list(item.get("symbols")),
                config={str(k): v for k, v in cfg.items()},
                confidence=_as_float(item.get("confidence"), default=0.5),
                source_span=item.get("source_span"),
                depends_on=_as_str_list(item.get("depends_on")),
            )
        )
    title = extraction.get("title") or (source.grobid.title if source.grobid else None)
    authors = _as_str_list(extraction.get("authors")) or (list(source.grobid.authors) if source.grobid else [])
    abstract = extraction.get("abstract") or (source.grobid.abstract if source.grobid else None)
    hardware_raw = extraction.get("hardware") or {}
    if not isinstance(hardware_raw, dict):
        hardware_raw = {}
    hardware = HardwareSpec(
        gpu_required=bool(hardware_raw.get("gpu_required")) if hardware_raw.get("gpu_required") is not None else False,
        min_gpu_memory_gb=_as_float_or_none(hardware_raw.get("min_gpu_memory_gb")),
        notes=hardware_raw.get("notes"),
    )
    return PaperFacts(
        title=title,
        authors=authors,
        abstract=abstract,
        main_claims=_as_str_list(extraction.get("main_claims")),
        datasets=_as_str_list(extraction.get("datasets")),
        metrics=_as_str_list(extraction.get("metrics")),
        symbols=_as_str_list(extraction.get("symbols")),
        results=results,
        hardware=hardware,
        extraction_method="llm",
        source_format=_normalize_format(source.source_format),
    )


def _normalize_format(fmt: str) -> str:
    if fmt in {"pdf", "markdown", "text"}:
        return fmt
    return "text"


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
    if not result_lines:
        return results
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
                source_span=line,
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


def _as_str_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return []


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
