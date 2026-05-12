---
name: paperharness
description: Use this skill to generate an agent-operable reproduce kit from a research paper and its GitHub repository using PaperHarness.
---
# PaperHarness

Use this skill when the user provides a research paper and a repository and asks to reproduce, audit, inspect, plan, or evaluate experiments.

PaperHarness does not reproduce papers. PaperHarness generates the harness that lets agents reproduce papers responsibly.

## What This Skill Does

This skill teaches the agent how to use the PaperHarness generator.

PaperHarness takes:

- a paper PDF, markdown, text file, or extracted arXiv text
- a local repository path or GitHub repository URL

and generates:

- `reprokit.yaml`
- a paper/repo-specific `skill/SKILL.md`
- a generated `repro` CLI
- `experiment_plan.md`
- `report_template.md`
- `missing_info.md`
- reference summaries and experiment maps

## Required Workflow

1. Check whether PaperHarness is installed:

   ```bash
   paperharness --help
   ```

   From a source checkout the equivalent is `PYTHONPATH=src python -m paperharness.cli --help`.

2. If the user gave a remote GitHub URL and remote cloning is not yet available in the installed version, clone the repository into a local working directory first.

3. **Extract paper facts (preferred for PDFs).** Run the deterministic prep step:

   ```bash
   paperharness extract-text <paper-path> --out paper-extract
   ```

   This produces in `paper-extract/`:

   - `paper.md` — markdown via Marker if `paperharness[parse]` is installed, otherwise raw PyMuPDF text. For `.txt` / `.md` inputs the original text is copied through.
   - `paper.sections.json` — GROBID-detected title/abstract/authors/sections, only if `--grobid-url` or `$GROBID_URL` is set.
   - `extraction_prompt.md` — a prompt instructing **you** (the calling agent) to emit a strict JSON object describing the paper's facts.
   - `extraction_schema.json` — the JSON schema the output must validate against.

4. **Fill the extraction JSON yourself, using your own model.** Read `paper-extract/extraction_prompt.md`, then emit one JSON object conforming to `extraction_schema.json`. Save it as `paper-extract/extraction.json`. Rules:

   - Every `results[*].source_span` must be a verbatim quote from `paper.md`.
   - Use `confidence <= 0.4` for results you infer rather than read directly.
   - Use `null` for fields the paper does not state; never invent values.
   - Datasets and metrics must be named exactly as the paper writes them.

5. **Build the reproduce kit with the extraction:**

   ```bash
   paperharness build \
     --paper <paper-path> \
     --repo <repo-path> \
     --extraction paper-extract/extraction.json
   ```

   If you skip the extraction step, `paperharness build` falls back to its regex extractor; the generated kit will mark `extraction_method: regex` and may report `No paper result candidates found.` as missing info. That is the correct behavior — uncertainty is preferable to fabrication.

6. Validate the generated kit:

   ```bash
   paperharness validate paperharness-output
   ```

7. Inspect the generated paper/repo-specific skill:

   ```bash
   cd paperharness-output/skill
   python scripts/repro.py inspect
   python scripts/repro.py list
   ```

8. Run smoke tests before any full experiment:

   ```bash
   python scripts/repro.py smoke
   ```

9. Do not run full training unless the user explicitly asks for it.

## Critical Rules

- Do not assume paper symbols and code variables have the same names.
- Do not invent mappings for missing paper variables, hyperparameters, datasets, checkpoints, or seeds.
- Do not rewrite target repository code just because an experiment is missing.
- Do not create duplicate helper scripts when the target repository already has commands or scripts.
- Treat `symbol_mappings` as hypotheses, not proof.
- Treat `implementation_status: partial_candidate` as a warning that the released repository may only implement part of the paper experiment.
- Treat `implementation_status: missing` as a blocker for full reproduction.
- Prefer partial reproducibility reports over silent failure.

## Reporting Requirements

Every report must include:

- exact commands used
- detected repo entrypoints
- paper results and expected metrics
- generated experiment IDs
- paper symbol to code variable mappings
- unmatched paper symbols
- missing datasets, checkpoints, seeds, and hyperparameters
- implementation gaps
- logs and artifact paths
- whether each result is mapped, runnable, blocked, failed, evaluated, or reported

## Output Handoff

After generating a kit, the generated `paperharness-output/skill/SKILL.md` becomes the source of truth for operating that specific paper/repository reproduction workflow.
