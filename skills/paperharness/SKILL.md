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

2. If working from the PaperHarness repository and the package is not installed, use:

   ```bash
   PYTHONPATH=src python -m paperharness.cli --help
   ```

3. If the user gave a remote GitHub URL and remote cloning is not yet available in the installed version, clone the repository into a local working directory first.

4. Build the reproduce kit:

   ```bash
   paperharness build --paper <paper-path> --repo <repo-path>
   ```

   or from a source checkout:

   ```bash
   PYTHONPATH=src python -m paperharness.cli build --paper <paper-path> --repo <repo-path>
   ```

5. Validate the generated kit:

   ```bash
   paperharness validate paperharness-output
   ```

6. Inspect the generated paper/repo-specific skill:

   ```bash
   cd paperharness-output/skill
   python scripts/repro.py inspect
   python scripts/repro.py list
   ```

7. Run smoke tests before any full experiment:

   ```bash
   python scripts/repro.py smoke
   ```

8. Do not run full training unless the user explicitly asks for it.

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
