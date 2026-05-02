

⸻

PaperHarness Project Specification

1. One-line Definition

PaperHarness is a compiler from research artifacts to agent-operable experiment protocols.

In plain words:

Given a research paper and its official GitHub repository, PaperHarness generates a reproducibility kit containing a skill, CLI wrapper, experiment plan, and report protocol so coding agents can execute experiments in a structured and auditable way.

This project is not a paper-reproduction agent.

It is a Reproduce Kit Generator.

⸻

1. Product Positioning

PaperHarness turns:

paper + GitHub repo

into:

skill + CLI + experiment plan + report protocol

Then an executor agent such as Codex, OpenClaw, Claude Code, OpenCode, or another coding agent can use the generated kit to set up the repo, run smoke tests, execute experiments, collect metrics, and write reproducibility reports.

OpenAI Codex skills are a good target format because a skill is a directory containing a required SKILL.md plus optional scripts/, references/, and assets/; the SKILL.md includes metadata such as name and description.  ￼ OpenAI’s API docs also describe skills as versioned file bundles with a SKILL.md manifest used to codify repeatable processes and workflows.  ￼

⸻

2. Core Philosophy

PaperHarness should behave like a compiler.

Research artifacts
  ├── paper.pdf / arXiv link / paper text
  └── GitHub repository
        ↓ parse
Facts
  ├── paper facts
  ├── repo facts
  └── command candidates
        ↓ lower
Experiment IR
  ├── environment
  ├── datasets
  ├── experiment definitions
  ├── expected paper results
  ├── runnable commands
  ├── risks
  └── reporting requirements
        ↓ generate
Reproduce Kit
  ├── SKILL.md
  ├── repro CLI
  ├── experiment_plan.md
  ├── report_template.md
  ├── references/
  └── scripts/

The main abstraction is:

Research artifacts are source code.
The ReproKit IR is the intermediate representation.
The generated skill, CLI, plan, and report are compiled outputs.

⸻

3. Non-goals

Do not build a full autonomous research agent.

Do not promise full paper reproduction.

Do not automatically run expensive training by default.

Do not assume every paper repo is runnable.

Do not silently guess missing datasets, checkpoints, or hyperparameters.

Do not modify the target repository unless explicitly requested.

PaperHarness succeeds when it creates a clear, auditable, agent-operable protocol, even if the final report says the paper cannot be fully reproduced.

⸻

4. MVP Scope

Version 0.1.0 should support:

Input:
  - local paper PDF or extracted markdown/text
  - local GitHub repo path or GitHub repo URL
Supported repos:
  - Python-based ML repos
  - PyTorch / Hugging Face / standard research-code style repos
  - repos with README instructions
  - repos with requirements.txt, environment.yml, pyproject.toml, or Dockerfile
  - repos with train.py, eval.py, test.py, scripts/*.sh, configs/*.yaml
Output:
  - a generated reproduce kit
  - a machine-readable reprokit.yaml
  - a generated SKILL.md
  - a generated repro CLI
  - an experiment plan
  - a report template
  - missing-info diagnostics

⸻

5. Top-level CLI

The project exposes one main CLI:

paperharness

Required commands:

paperharness build --paper ./paper.pdf --repo https://github.com/author/project
paperharness analyze --paper ./paper.pdf --repo ./repo
paperharness generate --ir ./paperharness-output/reprokit.yaml
paperharness validate ./paperharness-output
paperharness export ./paperharness-output --target codex

Recommended full command set:

paperharness build
paperharness analyze-paper
paperharness analyze-repo
paperharness match
paperharness generate
paperharness validate
paperharness export

paperharness build should run the full pipeline:

clone/load repo
parse paper
scan repo
find command candidates
match experiments
create ReproKit IR
generate kit files
validate generated kit

⸻

6. Generated Kit Layout

For an input repo named example-project, generate:

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
      expected_results.md
      risks.md
    assets/
      report_template.md

The generated skill/ directory should be directly usable as an agent skill folder.

⸻

7. Generated Kit CLI

Inside the kit, generate a lightweight CLI called:

repro

The repro CLI is not the same as paperharness.

paperharness = generator CLI
repro        = generated experiment runner CLI

Required generated commands:

repro inspect
repro list
repro status
repro setup
repro smoke
repro prepare-data
repro run <experiment_id>
repro evaluate <experiment_id>
repro collect
repro report

Command behavior:

repro inspect
  Show repo, paper, detected environment, available experiments, risks.
repro list
  List all experiments from reprokit.yaml.
repro status
  Show state of each experiment.
repro setup
  Run environment setup commands.
repro smoke
  Run minimal checks without full training.
repro prepare-data
  Run dataset preparation commands if available.
repro run <experiment_id>
  Run the mapped experiment command.
repro evaluate <experiment_id>
  Run evaluation command and collect metrics.
repro collect
  Gather logs, metrics, checkpoints, environment metadata.
repro report
  Generate reproducibility_report.md from collected results.

⸻

8. ReproKit IR

The most important file is:

reprokit.yaml

This is the source of truth for the generated skill and CLI.

Example schema:

schema_version: "0.1"
project:
  name: "example-project"
  repo_url: "https://github.com/author/project"
  repo_commit: null
  paper_path: "./paper.pdf"
  output_dir: "./paperharness-output"
paper:
  title: null
  authors: []
  abstract: null
  main_claims: []
  datasets: []
  metrics: []
  results:
    - id: "table1"
      label: "Table 1"
      description: "Main classification result"
      dataset: "CIFAR-10"
      metric: "accuracy"
      expected_value: 94.2
      tolerance: 1.0
      unit: "percent"
repo:
  language: "python"
  framework_candidates:
    - "pytorch"
  environment:
    type: "unknown"
    python_version: null
    install_commands:
      - "pip install -r requirements.txt"
    files:
      requirements: "requirements.txt"
      conda: null
      dockerfile: null
      pyproject: null
  entrypoints:
    setup:
      - "pip install -r requirements.txt"
    train:
      - "python train.py"
    evaluate:
      - "python evaluate.py"
    test: []
    scripts: []
datasets:
  - id: "cifar10"
    name: "CIFAR-10"
    source: null
    prepare_command: null
    status: "unknown"
    notes: []
experiments:
  - id: "table1_cifar10"
    paper_result_id: "table1"
    title: "Reproduce Table 1 on CIFAR-10"
    status: "mapped"
    confidence: 0.72
    setup:
      command: "pip install -r requirements.txt"
      expected_outputs: []
    data:
      command: null
      required_files: []
      notes:
        - "Dataset preparation command not found."
    smoke:
      command: "python train.py --help"
      timeout_seconds: 60
      success_criteria:
        - "command exits with code 0"
    run:
      command: "python train.py --config configs/cifar10.yaml"
      estimated_runtime: null
      hardware:
        gpu_required: true
        min_gpu_memory_gb: null
      expected_outputs:
        - "outputs/"
        - "checkpoints/"
    evaluate:
      command: "python evaluate.py --checkpoint outputs/best.pt"
      metrics_file: "outputs/metrics.json"
    expected:
      metric: "accuracy"
      value: 94.2
      tolerance: 1.0
      unit: "percent"
    evidence:
      - "README mentions CIFAR-10 training."
      - "configs/cifar10.yaml exists."
      - "train.py accepts a config argument."
    risks:
      - "Exact random seed not found."
      - "Dataset preprocessing is ambiguous."
reporting:
  required_sections:
    - "Summary"
    - "Environment"
    - "Commands"
    - "Datasets"
    - "Results"
    - "Comparison with paper"
    - "Missing information"
    - "Failure modes"
    - "Conclusion"
state:
  experiments:
    table1_cifar10:
      status: "not_started"
      last_updated: null
      logs: []
      artifacts: []

⸻

9. Experiment Status Model

Each experiment should have one of these statuses:

unmapped
mapped
setup_ready
data_ready
smoke_passed
running
evaluated
reported
blocked
failed

Status definitions:

unmapped
  Paper experiment exists but no repo command has been matched.
mapped
  A likely repo command exists, but it has not been validated.
setup_ready
  Environment setup command exists.
data_ready
  Dataset is available or preparation command completed.
smoke_passed
  Minimal command completed successfully.
running
  Full experiment is currently running or was started.
evaluated
  Metrics were produced.
reported
  Final report includes this experiment.
blocked
  Missing dataset, checkpoint, command, dependency, hardware, or other required info.
failed
  Command ran but exited unsuccessfully.

⸻

10. Paper Analyzer

Implement module:

src/paperharness/paper/

Files:

parse.py
extract_experiments.py
extract_results.py
summarize.py

Responsibilities:

- extract text from PDF
- optionally accept markdown/text directly
- identify title, abstract, datasets, metrics
- identify tables and figures if possible
- extract candidate experiment results
- extract hyperparameters if present
- extract claims and evaluation setup

MVP implementation can be mostly heuristic:

- search for sections named Experiments, Results, Evaluation, Ablation
- search for known dataset names
- search for table captions
- search for metric keywords such as accuracy, F1, BLEU, ROUGE, loss, perplexity
- emit candidate results with confidence scores

The analyzer should write:

references/paper_summary.md
references/expected_results.md

and structured data into reprokit.yaml.

⸻

11. Repo Analyzer

Implement module:

src/paperharness/repo/

Files:

clone.py
scan.py
detect_environment.py
detect_entrypoints.py
scan_readme.py
scan_configs.py

Responsibilities:

- clone GitHub repo if URL is provided
- detect repo language and framework
- detect dependency files
- detect setup commands
- detect train/eval/test scripts
- parse README for commands
- detect config files
- detect dataset/checkpoint instructions
- detect shell scripts

Important files to scan:

README.md
requirements.txt
environment.yml
pyproject.toml
setup.py
Dockerfile
Makefile
train.py
eval.py
evaluate.py
test.py
scripts/*.sh
scripts/*.py
configs/*.yaml
configs/*.yml
configs/*.json
examples/*
notebooks/*

Command candidate extraction should look for:

pip install ...
conda env create ...
python train.py ...
python eval.py ...
python evaluate.py ...
bash scripts/...
make ...

The analyzer should write:

references/repo_summary.md

and structured data into reprokit.yaml.

⸻

12. Experiment Matcher

Implement module:

src/paperharness/matcher/

Files:

match.py
score.py
missing.py

Responsibilities:

- match paper result candidates to repo command candidates
- assign confidence scores
- attach evidence
- detect missing information
- mark experiments as mapped, unmapped, or blocked

Initial scoring can be simple and rule-based.

Suggested signals:

dataset name overlap
metric name overlap
config filename overlap
script name overlap
README command proximity
paper table caption overlap
method/model name overlap

Example scoring logic:

+0.25 if dataset name appears in command/config path
+0.20 if metric appears near command in README
+0.20 if config name matches paper experiment
+0.15 if train/eval entrypoint found
+0.10 if README describes same experiment
+0.10 if expected output path is documented

Confidence bands:

0.80 - 1.00: high
0.50 - 0.79: medium
0.20 - 0.49: low
0.00 - 0.19: unmapped

Never hide uncertainty. Every generated experiment should include evidence and risks.

⸻

13. Generator

Implement module:

src/paperharness/generate/

Files:

skill.py
cli.py
plan.py
report.py
references.py

Responsibilities:

- generate SKILL.md
- generate repro CLI
- generate experiment_plan.md
- generate report_template.md
- generate missing_info.md
- generate references

Use Jinja2 templates:

src/paperharness/templates/
  SKILL.md.j2
  repro.py.j2
  experiment_plan.md.j2
  report_template.md.j2
  missing_info.md.j2
  paper_summary.md.j2
  repo_summary.md.j2
  experiment_map.md.j2

⸻

14. Generated SKILL.md Template

Generate a skill like this:

---
name: reproduce-{{ project.name }}
description: Use this skill to run, evaluate, and report reproducibility experiments for {{ project.name }} using the generated PaperHarness kit.
---
# Reproduce {{ project.name }}
Use this skill when asked to reproduce, validate, inspect, debug, or report experiments from this paper repository.
## Source of truth
Always read `reprokit.yaml` before running commands.
Do not guess missing datasets, checkpoints, hyperparameters, or hardware requirements. If something is missing, mark the experiment as blocked and explain why.
## Required workflow
1. Inspect the kit:
   `python scripts/repro.py inspect`
2. List experiments:
   `python scripts/repro.py list`
3. Set up the environment:
   `python scripts/repro.py setup`
4. Run smoke tests before full experiments:
   `python scripts/repro.py smoke`
5. Prepare data if a data command is available:
   `python scripts/repro.py prepare-data`
6. Run one experiment at a time:
   `python scripts/repro.py run <experiment_id>`
7. Evaluate the experiment:
   `python scripts/repro.py evaluate <experiment_id>`
8. Collect logs and metrics:
   `python scripts/repro.py collect`
9. Write the reproducibility report:
   `python scripts/repro.py report`
## Safety and cost rules
- Do not run full training before smoke tests pass.
- Do not launch expensive GPU jobs unless explicitly requested.
- Prefer short validation runs before full experiments.
- Record every command, environment detail, commit hash, seed, dataset version, and metric.
- If an experiment fails, preserve logs and report the exact failure.
- Prefer partial reproducibility reports over silent failure.
## Reporting requirements
The final report must include:
- paper target result
- reproduced result
- exact command used
- environment
- hardware
- dataset source and version
- random seeds
- logs and artifact paths
- missing information
- failure modes
- confidence level

⸻

15. Generated Experiment Plan

experiment_plan.md should be readable by both humans and agents.

Required sections:

# Experiment Plan
## Project
## Paper Summary
## Repository Summary
## Reproduction Strategy
## Experiments
### Experiment: <id>
- Paper target:
- Dataset:
- Metric:
- Expected value:
- Setup command:
- Data command:
- Smoke command:
- Run command:
- Evaluation command:
- Expected outputs:
- Risks:
- Confidence:
## Recommended Execution Order
1. inspect
2. setup
3. smoke
4. prepare-data
5. run experiment 1
6. evaluate experiment 1
7. collect
8. report
## Blocking Issues
## Reporting Protocol

⸻

16. Generated Report Template

report_template.md should become reproducibility_report.md after execution.

Template:

# Reproducibility Report
## Summary
- Project:
- Paper:
- Repository:
- Commit:
- Reproduction status:
- Reproducibility level:
## Environment
- OS:
- Python:
- CUDA:
- GPU:
- CPU:
- RAM:
- Package manager:
- Dependency files:
## Commands Run
```bash
# commands go here

Dataset Preparation

* Dataset:
* Source:
* Version:
* Preprocessing:
* Missing data issues:

Experiments

Experiment	Paper target	Actual result	Status	Confidence

Detailed Results

<experiment_id>

* Paper expected result:
* Actual result:
* Difference:
* Within tolerance:
* Metrics file:
* Logs:
* Artifacts:
* Notes:

Missing Information

Failure Modes

Conclusion

---
## 17. Generated `repro.py`
The generated CLI should be simple, robust, and transparent.
Use Python standard library plus PyYAML if available.
The generated `repro.py` should:
```text
- load reprokit.yaml
- print experiment list
- run commands using subprocess
- write logs to runs/<experiment_id>/
- store command metadata
- update simple status files
- collect metrics if metrics path exists
- generate markdown report

Generated runtime layout:

runs/
  table1_cifar10/
    setup.log
    smoke.log
    run.log
    evaluate.log
    metrics.json
    metadata.json
reproducibility_report.md

Important behavior:

- print commands before running them
- require explicit experiment_id for run/evaluate
- fail gracefully if command is missing
- mark missing command as blocked
- preserve logs
- never delete user files

⸻

18. Validation

Implement:

paperharness validate ./paperharness-output

Validation checks:

- reprokit.yaml exists
- skill/SKILL.md exists
- generated repro CLI exists
- every experiment has an id
- every mapped experiment has at least one command
- every command has evidence or warning
- missing info is documented
- report template exists
- experiment plan exists

Validation output example:

✅ reprokit.yaml found
✅ skill/SKILL.md found
✅ 3 experiments found
✅ 2 mapped experiments
⚠️ 1 unmapped experiment
⚠️ dataset command missing for table2
❌ no setup command found

Validation should return non-zero only for structural errors, not for ordinary reproducibility uncertainty.

⸻

19. Reproducibility Levels

Use this standardized scale:

Level 0: Parsed
  Paper and repo were analyzed.
Level 1: Mapped
  Paper experiments were mapped to likely repo commands.
Level 2: Runnable
  Environment setup and smoke tests can run.
Level 3: Reproduced
  At least one full experiment produced metrics within tolerance.
Level 4: Verified
  Results were reproduced across multiple seeds or environments.

The generated report should include one of these levels.

⸻

20. Python Package Structure

Create this repository layout:

paperharness/
  README.md
  PROJECT_SPEC.md
  pyproject.toml
  src/
    paperharness/
      __init__.py
      cli.py
      paper/
        __init__.py
        parse.py
        extract_experiments.py
        extract_results.py
        summarize.py
      repo/
        __init__.py
        clone.py
        scan.py
        detect_environment.py
        detect_entrypoints.py
        scan_readme.py
        scan_configs.py
      matcher/
        __init__.py
        match.py
        score.py
        missing.py
      ir/
        __init__.py
        schema.py
        validate.py
        io.py
      generate/
        __init__.py
        skill.py
        cli_wrapper.py
        plan.py
        report.py
        references.py
      templates/
        SKILL.md.j2
        repro.py.j2
        experiment_plan.md.j2
        report_template.md.j2
        missing_info.md.j2
        paper_summary.md.j2
        repo_summary.md.j2
        experiment_map.md.j2
      utils/
        __init__.py
        commands.py
        files.py
        logging.py
  examples/
    minimal_pytorch/
      paper.txt
      repo/
        README.md
        requirements.txt
        train.py
        evaluate.py
        configs/
          cifar10.yaml
  tests/
    test_cli.py
    test_repo_scan.py
    test_ir_validation.py
    test_generation.py

⸻

21. Dependencies

Use a small dependency set for MVP:

[project]
name = "paperharness"
version = "0.1.0"
description = "Generate agent-operable reproduction kits from research papers and GitHub repositories."
requires-python = ">=3.10"
dependencies = [
  "typer>=0.12",
  "rich>=13.0",
  "pydantic>=2.0",
  "pyyaml>=6.0",
  "jinja2>=3.0",
  "gitpython>=3.1",
  "pymupdf>=1.24"
]
[project.scripts]
paperharness = "paperharness.cli:app"

Testing:

[project.optional-dependencies]
dev = [
  "pytest",
  "ruff",
  "mypy"
]

⸻

22. Implementation Milestones

Milestone 1: Skeleton

Implement:

- pyproject.toml
- package structure
- Typer CLI
- build command stub
- validate command stub
- example fixture repo

Acceptance:

paperharness --help
paperharness build --help
pytest

⸻

Milestone 2: Repo Scanner

Implement:

- local repo scan
- README command extraction
- dependency file detection
- train/eval/test script detection
- config file detection

Acceptance:

paperharness analyze-repo examples/minimal_pytorch/repo

Should output structured repo facts.

⸻

Milestone 3: Paper Parser

Implement:

- parse PDF with PyMuPDF
- parse .txt and .md paper files
- extract title candidate
- extract experiment/result candidates
- extract dataset and metric candidates

Acceptance:

paperharness analyze-paper examples/minimal_pytorch/paper.txt

Should output structured paper facts.

⸻

Milestone 4: IR

Implement:

- Pydantic schema
- YAML read/write
- validation
- status model

Acceptance:

paperharness validate-ir examples/minimal_pytorch/reprokit.yaml

⸻

Milestone 5: Matcher

Implement:

- experiment-command matching
- confidence scoring
- evidence generation
- missing-info detection

Acceptance:

paperharness match --paper-facts paper.yaml --repo-facts repo.yaml

Should generate experiments with confidence and risks.

⸻

Milestone 6: Kit Generator

Implement:

- generate SKILL.md
- generate repro.py
- generate experiment_plan.md
- generate report_template.md
- generate references

Acceptance:

paperharness build --paper examples/minimal_pytorch/paper.txt --repo examples/minimal_pytorch/repo

Should create paperharness-output/.

⸻

Milestone 7: Generated CLI

Implement generated repro.py commands:

inspect
list
status
setup
smoke
run
evaluate
collect
report

Acceptance:

cd paperharness-output/skill
python scripts/repro.py inspect
python scripts/repro.py list
python scripts/repro.py smoke
python scripts/repro.py report

⸻

Milestone 8: Tests and README

Implement:

- tests for scanner
- tests for parser
- tests for IR validation
- tests for generated files
- README with quickstart

Acceptance:

pytest
ruff check .

⸻

23. README First Draft

Create README.md:

# PaperHarness
PaperHarness is a compiler from research artifacts to agent-operable experiment protocols.
It takes a research paper and its GitHub repository, then generates a reproduce kit containing:
- an agent skill
- a CLI wrapper
- an experiment plan
- a report protocol
- missing-information diagnostics
PaperHarness is not a paper-reproduction agent. It generates the kit that coding agents use to reproduce experiments safely and systematically.
## Quickstart
```bash
paperharness build --paper ./paper.pdf --repo https://github.com/author/project
cd paperharness-output/skill
python scripts/repro.py inspect
python scripts/repro.py smoke
python scripts/repro.py report

Outputs

paperharness-output/
  reprokit.yaml
  experiment_plan.md
  report_template.md
  missing_info.md
  skill/
    SKILL.md
    scripts/
    references/
    assets/

Reproducibility levels

* Level 0: Parsed
* Level 1: Mapped
* Level 2: Runnable
* Level 3: Reproduced
* Level 4: Verified

---
## 24. Codex Implementation Instruction
Use this instruction when giving the project to Codex:
```text
You are implementing PaperHarness.
PaperHarness is a compiler from research artifacts to agent-operable experiment protocols.
Do not build an autonomous paper-reproduction agent.
Build a Reproduce Kit Generator.
Inputs:
- research paper PDF, markdown, or text
- local GitHub repository path or GitHub URL
Outputs:
- reprokit.yaml
- SKILL.md
- generated repro CLI
- experiment_plan.md
- report_template.md
- references/
- missing_info.md
Implement the project in Python using Typer, Pydantic, PyYAML, Jinja2, GitPython, Rich, and PyMuPDF.
Start with a minimal but working MVP:
1. Create package skeleton.
2. Implement repo scanner.
3. Implement paper parser.
4. Implement ReproKit IR.
5. Implement matcher.
6. Implement kit generator.
7. Implement generated repro CLI.
8. Add tests and example fixture.
Prioritize correctness, transparency, and graceful failure.
Never pretend an experiment is runnable if commands, data, checkpoints, or hardware requirements are missing. Instead, mark it as blocked and explain why.

⸻

25. MVP Success Criteria

The MVP is successful when this works:

paperharness build \
  --paper examples/minimal_pytorch/paper.txt \
  --repo examples/minimal_pytorch/repo

and produces:

paperharness-output/
  reprokit.yaml
  experiment_plan.md
  report_template.md
  missing_info.md
  skill/
    SKILL.md
    scripts/repro.py
    references/paper_summary.md
    references/repo_summary.md
    references/experiment_map.md

Then this should work:

cd paperharness-output/skill
python scripts/repro.py inspect
python scripts/repro.py list
python scripts/repro.py smoke
python scripts/repro.py report

The generated report may say:

Status: partially mapped
Level: 1 - Mapped
Blocked issues:
- dataset preparation command not found
- exact seed missing
- checkpoint URL missing

That is acceptable and expected.

⸻

26. Design Principle to Preserve

Keep this sentence at the top of the project:

PaperHarness does not reproduce papers.
PaperHarness generates the harness that lets agents reproduce papers responsibly.

That distinction is the product.