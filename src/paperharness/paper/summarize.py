"""Produce a human/agent-readable summary of :class:`PaperFacts`.

The generated kit needs a ``paper_summary.md`` that an agent can read before
deciding how to map experiments. The previous one-line stub did not capture
authors, claims, or the per-result quantitative table — this module produces a
structured multi-section markdown summary.
"""

from __future__ import annotations

from paperharness.ir.schema import PaperFacts


def summarize_paper(facts: PaperFacts) -> str:
    """One-line headline kept for backwards-compatible callers."""
    datasets = ", ".join(facts.datasets) or "unknown datasets"
    metrics = ", ".join(facts.metrics) or "unknown metrics"
    return f"{facts.title or 'Untitled paper'}; datasets={datasets}; metrics={metrics}"


def summarize_paper_markdown(facts: PaperFacts) -> str:
    """Produce a multi-section markdown summary for skill/references/paper_summary.md."""
    lines: list[str] = []
    lines.append(f"# {facts.title or 'Untitled paper'}")
    lines.append("")
    lines.append(
        f"_Source format: {facts.source_format}; extraction: {facts.extraction_method}._"
    )
    lines.append("")
    if facts.authors:
        lines.append("**Authors:** " + ", ".join(facts.authors))
        lines.append("")
    if facts.abstract:
        lines.append("## Abstract")
        lines.append("")
        lines.append(facts.abstract.strip())
        lines.append("")
    lines.append("## Datasets and metrics")
    lines.append("")
    lines.append("- Datasets: " + (", ".join(facts.datasets) or "_none detected_"))
    lines.append("- Metrics: " + (", ".join(facts.metrics) or "_none detected_"))
    lines.append("- Symbols: " + (", ".join(facts.symbols) or "_none detected_"))
    lines.append("")
    hw = facts.hardware
    if hw and (hw.gpu_required or hw.min_gpu_memory_gb or hw.notes):
        lines.append("## Hardware requirements")
        lines.append("")
        if hw.gpu_required:
            lines.append("- GPU required: yes")
        if hw.min_gpu_memory_gb:
            lines.append(f"- Minimum GPU memory: {hw.min_gpu_memory_gb} GB")
        if hw.notes:
            lines.append(f"- Notes: {hw.notes}")
        lines.append("")
    if facts.main_claims:
        lines.append("## Main claims")
        lines.append("")
        for claim in facts.main_claims:
            lines.append(f"- {claim}")
        lines.append("")
    if facts.results:
        lines.append("## Reported results")
        lines.append("")
        lines.append("| id | dataset | metric | value | unit | confidence | source |")
        lines.append("|----|---------|--------|-------|------|------------|--------|")
        for r in facts.results:
            value = "—" if r.expected_value is None else str(r.expected_value)
            unit = r.unit or ""
            source = (r.source_span or "").replace("\n", " ").strip()
            if len(source) > 80:
                source = source[:77] + "…"
            source = source.replace("|", "\\|") or "—"
            lines.append(
                f"| `{r.id}` | {r.dataset or '—'} | {r.metric or '—'} | "
                f"{value} | {unit} | {r.confidence:.2f} | {source} |"
            )
        lines.append("")
    else:
        lines.append("## Reported results")
        lines.append("")
        lines.append("_No paper results extracted. See `missing_info.md`._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
