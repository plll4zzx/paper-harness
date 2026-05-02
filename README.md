# PaperHarness

PaperHarness generates the harness that lets agents reproduce papers responsibly.

PaperHarness turns a research paper and its GitHub repository into an agent-operable reproduce kit:

```text
paper.pdf / arXiv text + GitHub repo
        |
        v
reprokit.yaml + agent skill + repro CLI + experiment plan + report protocol
```

It is designed for Codex, OpenClaw, Claude Code, OpenCode, and other coding agents that need to reproduce or audit research code without repeatedly rediscovering the same context.

## The Pain

Reproducing a paper from its repository is often slow before any experiment even runs.

You open the paper and the code, but it is not obvious where to start:

- paper symbols rarely match code variable names
- paper experiments are often only partially implemented in the released repo
- datasets, checkpoints, seeds, and preprocessing details may be missing
- table names, config files, scripts, and README commands are scattered across the repo
- every experiment requires rereading many files to find the right command
- agents often miss existing functionality and write new scripts for things the repo already supports
- repeated code exploration burns time, context window, and tokens
- debugging becomes expensive because the agent has no stable experiment protocol

PaperHarness addresses this by compiling the paper and repository into a structured protocol before experiments begin.

## What PaperHarness Generates

Given a paper and repo, PaperHarness creates:

- `reprokit.yaml`: machine-readable source of truth
- `skill/SKILL.md`: an agent skill for the specific paper/repo pair
- `skill/scripts/repro.py`: generated experiment runner
- `experiment_plan.md`: human- and agent-readable execution plan
- `report_template.md`: reproducibility report protocol
- `missing_info.md`: missing datasets, checkpoints, symbols, commands, and implementation gaps
- `skill/references/`: paper summary, repo summary, experiment map, expected results, and risks

The generated kit is intentionally conservative. If a paper variable does not map cleanly to code, or if the repo appears to implement only part of an experiment, the kit records that uncertainty instead of pretending the experiment is reproducible.

## Why This Helps Agents

Without PaperHarness, an agent usually has to rediscover the repository every time:

```text
read paper -> inspect repo -> guess commands -> run something -> fail -> inspect more files -> write helper scripts -> debug
```

With PaperHarness:

```text
analyze once -> generate kit -> follow repro protocol -> preserve logs -> write report
```

The generated kit tells the agent:

- which commands already exist
- which experiments are mapped, unmapped, blocked, or only partial candidates
- which paper symbols are unmatched in code
- which datasets, checkpoints, seeds, or hyperparameters are missing
- which smoke tests must pass before full training
- how to collect logs and write a reproducibility report

This reduces duplicated scripts, accidental reimplementation, repeated file scanning, and token-heavy debugging loops.

## Install PaperHarness

From this repository:

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
pytest
```

Then:

```bash
paperharness --help
```

You can also run without installation:

```bash
PYTHONPATH=src python -m paperharness.cli --help
```

## Quickstart

Generate a reproduce kit:

```bash
paperharness build \
  --paper examples/minimal_pytorch/paper.txt \
  --repo examples/minimal_pytorch/repo
```

Inspect the generated kit:

```bash
cd paperharness-output/skill
python scripts/repro.py inspect
python scripts/repro.py list
python scripts/repro.py smoke
python scripts/repro.py report
```

The output looks like:

```text
paperharness-output/
  reprokit.yaml
  experiment_plan.md
  report_template.md
  missing_info.md
  skill/
    SKILL.md
    scripts/
      repro.py
      setup_env.py
      smoke_test.py
      run_experiment.py
      evaluate.py
      collect_results.py
      write_report.py
    references/
      paper_summary.md
      repo_summary.md
      experiment_map.md
    assets/
      report_template.md
```

## Agent Skill Installation

This repository includes a PaperHarness usage skill at:

```text
skills/paperharness/SKILL.md
```

An agent can install it by copying that directory into its skill directory.

For Codex-style skills:

```bash
mkdir -p ~/.codex/skills
cp -R skills/paperharness ~/.codex/skills/
```

After installation, the agent should use the PaperHarness skill whenever it is given:

- a research paper PDF, text, markdown, or arXiv-derived text
- a local repository path or GitHub repository URL
- a request to reproduce, audit, inspect, or plan experiments

The installed PaperHarness skill teaches the agent how to run this generator. The generator then creates a second skill specific to the target paper and repository.

In other words:

```text
PaperHarness skill
  teaches the agent how to generate kits

Generated reproduce skill
  teaches the agent how to operate one specific paper/repo kit
```

## Core CLI

```bash
paperharness build --paper ./paper.pdf --repo ./repo
paperharness analyze-paper ./paper.pdf
paperharness analyze-repo ./repo
paperharness generate --ir ./paperharness-output/reprokit.yaml
paperharness validate ./paperharness-output
paperharness export ./paperharness-output --target codex
```

## Reproducibility Levels

- Level 0: Parsed
- Level 1: Mapped
- Level 2: Runnable
- Level 3: Reproduced
- Level 4: Verified

The MVP mostly targets Level 0 and Level 1, with smoke-test support for moving toward Level 2.

## Current Status

This is an early MVP. It supports local paper text/markdown/PDF input, local Python research repositories, heuristic command detection, heuristic paper result extraction, conservative experiment matching, and generated Codex-style reproduce kits.

Remote GitHub cloning and deeper semantic paper/code alignment are planned next.
