from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paperharness.ir.schema import PaperFacts, ReviewRequiredSpec


EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["title", "datasets", "metrics", "results"],
    "properties": {
        "title": {"type": ["string", "null"]},
        "authors": {"type": "array", "items": {"type": "string"}},
        "abstract": {"type": ["string", "null"]},
        "datasets": {"type": "array", "items": {"type": "string"}},
        "metrics": {"type": "array", "items": {"type": "string"}},
        "symbols": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Bare paper notation that downstream code might define as a variable: "
                "math symbols (alpha, lambda, tau), or hyperparameter names the paper writes (lr, epochs). "
                "DO NOT put '=value' here. DO NOT put 'this experiment used wm_name=KGW' here."
            ),
        },
        "main_claims": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Verbatim sentences stating the paper's headline claims.",
        },
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "label", "dataset", "metric", "confidence"],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "dataset": {"type": ["string", "null"]},
                    "metric": {"type": ["string", "null"]},
                    "expected_value": {"type": ["number", "string", "null"]},
                    "tolerance": {"type": ["number", "null"]},
                    "unit": {"type": ["string", "null"]},
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Subset of the top-level `symbols` that THIS result depends on. "
                            "Bare names only (e.g. 'alpha'). Not 'alpha=0.5'."
                        ),
                    },
                    "config": {
                        "type": "object",
                        "additionalProperties": {"type": ["string", "number", "boolean", "null"]},
                        "description": (
                            "Experiment-instance configuration: which dataset split, which model, "
                            "which hyperparameter VALUES this row used. Example: "
                            "{'wm_name': 'KGW', 'atk_style': 'char', 'max_edit_rate': 0.1}. "
                            "This is the right place for 'wm_name=KGW'-style values."
                        ),
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "0.0-1.0 reflecting how directly the result is stated in the paper.",
                    },
                    "source_span": {
                        "type": ["string", "null"],
                        "description": "Verbatim quote from the paper or table caption supporting this result.",
                    },
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "ids of other results in this list that must be reproduced first "
                            "(e.g. a guided attack depends on training a reference detector)."
                        ),
                    },
                },
            },
        },
        "reproduction_commands": {
            "type": "array",
            "description": (
                "Commands the paper itself prints (Artifact Appendix, README quoted in paper, code blocks). "
                "PaperHarness will route these into the experiments' run/setup/data/evaluate phases."
            ),
            "items": {
                "type": "object",
                "required": ["phase", "command", "source_span"],
                "properties": {
                    "phase": {
                        "type": "string",
                        "enum": ["setup", "data", "smoke", "run", "evaluate"],
                    },
                    "command": {"type": "string", "description": "Shell command exactly as written in the paper."},
                    "applies_to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Result ids (matching `results[*].id`) this command reproduces. "
                            "Empty/omitted = applies to every experiment."
                        ),
                    },
                    "source_span": {
                        "type": "string",
                        "description": "Verbatim quote of the surrounding sentence or section heading.",
                    },
                    "notes": {"type": ["string", "null"]},
                },
            },
        },
        "hardware": {
            "type": "object",
            "description": "Hardware requirements stated by the paper.",
            "properties": {
                "gpu_required": {"type": ["boolean", "null"]},
                "min_gpu_memory_gb": {"type": ["number", "null"]},
                "notes": {"type": ["string", "null"]},
            },
        },
    },
}


PROMPT_TEMPLATE = """\
# PaperHarness — Paper Facts Extraction Task

You are extracting structured facts from one research paper so a downstream agent can plan reproducibility experiments. **Do not invent facts.** Anything you are not confident about should either be omitted or have low `confidence` and an explanation in `description`.

## CRITICAL: prefer the Artifact Appendix

Systems and security papers (USENIX/NDSS/OSDI/IEEE S&P/CCS) often include an **Artifact Appendix** (sections titled "Artifact Appendix", "Artifact Evaluation", "Reproducibility Appendix", "Major Claims", or "Experiment Workflow"). If the paper has one, treat it as the **authoritative source** for:

- `reproduction_commands` — copy the exact shell commands the appendix gives.
- `results[*].config` — the values the appendix says to use.
- `main_claims` — promote the appendix's "Major Claims" (often labeled C1, C2, ...) into `main_claims`, and prefer their wording over scattered prose elsewhere.

When an appendix exists, the main body's numbers are still the *target metrics* (`results[*].expected_value`), but the appendix's commands should drive `reproduction_commands` even if the main body also mentions commands.

## Output

Return **a single JSON object** that validates against the schema below. No prose, no markdown, no fenced block — just JSON.

### JSON schema

```json
{schema}
```

### Field guidance

- `results` — one entry per *reported quantitative result* (table cell, figure annotation, or in-text number) that the paper claims to achieve. Each entry's `source_span` MUST quote text from the paper. If a result is implied but not directly stated, set `confidence <= 0.4`.
- `datasets` — dataset names exactly as the paper writes them (e.g. "CIFAR-10", not "cifar10").
- `metrics` — metric short names (e.g. "accuracy", "BLEU", "PSNR", "ASR").
- `symbols` — **bare variable names** the paper uses that downstream code might also use: math symbols (`alpha`, `lambda`, `tau`) and parameter names (`lr`, `epochs`, `batch_size`). **Do NOT put values here** (write `alpha`, not `alpha=0.5`). **Do NOT put "this experiment used wm_name=KGW" here** — that goes in `results[*].config`.
- `results[*].symbols` — subset of the top-level `symbols`; just the names this specific result depends on.
- `results[*].config` — the *concrete values* this specific result used. Example: `{"wm_name": "KGW", "atk_style": "char", "max_edit_rate": 0.1}`. This is the right field for "the table row's column headers translated to k/v".
- `reproduction_commands` — **scan the paper for shell commands**, especially in Artifact Appendix / Reproducibility sections / inline code blocks. Each entry says which `phase` it belongs to and which `results[*].id` it reproduces. Empty `applies_to` = applies to every result. **Quote the full command verbatim**, including all CLI flags.
- `hardware` — if the paper states GPU/memory/CPU requirements (e.g. "NVIDIA GPU with at least 10GB memory"), fill it in.
- `main_claims` — at most 5 verbatim sentences capturing the paper's headline claims.
- `id` — short stable slug like `cifar10_acc` or `tab2_kgw_char_er01`.
- Use null instead of guessing when a field is genuinely absent in the paper.

## Paper (markdown)

The paper text follows. It may include tables in GFM format from PDF→markdown conversion. Prefer table cells over loose paragraph numbers when both are available.

---

{paper_text}
"""


def build_extraction_prompt(
    paper_text: str,
    grobid_sections: dict | None = None,
) -> str:
    schema_json = json.dumps(EXTRACTION_SCHEMA, indent=2)
    sections_block = ""
    if grobid_sections:
        sections_block = (
            "\n\n## GROBID-detected structure (use as cross-check)\n\n"
            "```json\n"
            + json.dumps(_summarize_grobid(grobid_sections), indent=2)
            + "\n```\n"
        )
    return (
        PROMPT_TEMPLATE
        .replace("{schema}", schema_json)
        .replace("{paper_text}", paper_text + sections_block)
    )


def load_extraction(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(line for line in raw.splitlines() if not line.strip().startswith("```"))
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("extraction file must be a JSON object")
    return data


PHASE_TO_FIELD = {
    "setup": "setup",
    "data": "data",
    "smoke": "smoke",
    "run": "run",
    "evaluate": "evaluate",
}


def attach_reproduction_commands(
    experiments: list,
    repo_facts,
    extraction: dict,
) -> list[str]:
    """Merge LLM-extracted commands into experiments/repo. Return human-readable log lines."""
    log: list[str] = []
    commands = extraction.get("reproduction_commands") or []
    if not commands:
        return log

    paper_result_to_exp: dict[str, list] = {}
    for exp in experiments:
        if exp.paper_result_id:
            paper_result_to_exp.setdefault(exp.paper_result_id, []).append(exp)

    for cmd in commands:
        if not isinstance(cmd, dict):
            continue
        phase = cmd.get("phase")
        command = cmd.get("command")
        if phase not in PHASE_TO_FIELD or not command:
            continue
        source_span = cmd.get("source_span")
        targets_raw = cmd.get("applies_to") or []
        targets = [t for t in targets_raw if isinstance(t, str)]

        if targets:
            target_exps: list = []
            for t in targets:
                target_exps.extend(paper_result_to_exp.get(t, []))
                target_exps.extend(e for e in experiments if e.id == t)
            # de-dup while preserving order
            seen_ids = set()
            target_exps = [e for e in target_exps if not (e.id in seen_ids or seen_ids.add(e.id))]
        else:
            target_exps = list(experiments)

        if phase == "setup" and command not in repo_facts.environment.install_commands:
            repo_facts.environment.install_commands.insert(0, command)

        field = PHASE_TO_FIELD[phase]
        for exp in target_exps:
            spec = getattr(exp, field)
            if spec.command and spec.source == "repo":
                # Paper-stated command beats repo guess
                _replace_command(spec, command, source_span)
                log.append(f"{exp.id}.{field}: replaced repo-detected command with paper-stated one")
            elif not spec.command:
                _replace_command(spec, command, source_span)
                log.append(f"{exp.id}.{field}: attached paper-stated command")

    # Recompute implementation_status / status / risks now that paper-stated commands are in.
    for exp in experiments:
        if exp.run.command and exp.evaluate.command:
            exp.implementation_status = "complete_candidate"
        elif exp.run.command:
            exp.implementation_status = "partial_candidate"
        if exp.run.command and exp.status in {"unmapped", "blocked"}:
            exp.status = "mapped"
            # Drop now-stale "no run command found" risk.
            exp.risks = [r for r in exp.risks if "No run command found" not in r]
            # Bump confidence since we now have a paper-stated command.
            exp.confidence = min(1.0, max(exp.confidence, 0.6))

    return log


def _replace_command(spec, command: str, source_span: str | None) -> None:
    spec.command = command
    spec.source = "paper"
    if source_span:
        spec.source_span = source_span


def review_items_from_facts(
    facts: PaperFacts,
    threshold: float = 0.6,
) -> list[ReviewRequiredSpec]:
    items: list[ReviewRequiredSpec] = []
    if facts.extraction_method != "llm":
        return items
    for result in facts.results:
        if result.confidence < threshold:
            items.append(
                ReviewRequiredSpec(
                    experiment_id=result.id,
                    issue_type="low_confidence_paper_result",
                    symbols=result.symbols,
                    severity="review",
                    message=(
                        f"LLM-extracted result {result.id} has confidence "
                        f"{result.confidence:.2f} < {threshold:.2f}. "
                        f"Source span: {result.source_span or 'not provided'}"
                    ),
                )
            )
    return items


def _summarize_grobid(sections: dict) -> dict:
    return {
        "title": sections.get("title"),
        "authors": sections.get("authors") or [],
        "section_heads": [s.get("head") for s in (sections.get("sections") or []) if s.get("head")],
    }
