from __future__ import annotations

import re

from paperharness.ir.schema import CommandSpec, DatasetSpec, EvidenceSpec, ExperimentSpec, PaperFacts, RepoFacts


def build_experiments(paper: PaperFacts, repo: RepoFacts) -> tuple[list[ExperimentSpec], list[DatasetSpec], list[str]]:
    datasets = [DatasetSpec(id=_slug(d), name=d, notes=["Dataset source not confirmed from repository."]) for d in paper.datasets]
    experiments: list[ExperimentSpec] = []
    missing: list[str] = []
    results = paper.results or []
    if not results:
        missing.append("No paper result candidates found.")
    for result in results:
        score, evidence, risks = _score(result.dataset, result.metric, repo)
        run_command = _best_run_command(result.dataset, repo)
        eval_command = _best_eval_command(repo)
        smoke_command = _smoke_command(run_command, repo)
        setup_command = repo.environment.install_commands[0] if repo.environment.install_commands else None
        symbol_mappings, unmatched_paper, unmatched_code = _symbol_mapping(result.symbols, repo.code_symbols)
        implementation_status = _implementation_status(run_command, eval_command, score)
        status = "mapped" if score >= 0.2 and run_command else "unmapped"
        if implementation_status == "missing":
            status = "blocked"
        if unmatched_paper:
            risks.append("Paper symbols do not map cleanly to code variables: " + ", ".join(unmatched_paper[:10]))
        if implementation_status == "partial_candidate":
            risks.append("Repository appears to implement only part of this experiment.")
        if not run_command:
            risks.append("No run command found for this paper result.")
            missing.append(f"No run command found for {result.id}.")
        if result.dataset and not any(
            _name_appears_in(result.dataset, c) for c in repo.command_candidates + repo.config_files
        ):
            risks.append(f"Dataset {result.dataset} not found in commands or config paths.")
            missing.append(f"Dataset mapping missing for {result.dataset}.")
        exp_id = f"{result.id}_{_slug(result.dataset or 'unknown')}"
        experiments.append(
            ExperimentSpec(
                id=exp_id,
                paper_result_id=result.id,
                title=f"Reproduce {result.label}",
                status=status,
                confidence=round(score, 2),
                implementation_status=implementation_status,
                depends_on=[f"{dep}_{_slug(result.dataset or 'unknown')}" for dep in result.depends_on],
                setup=CommandSpec(command=setup_command),
                data=CommandSpec(command=None, success_criteria=["dataset is available or issue is documented"]),
                smoke=CommandSpec(command=smoke_command, timeout_seconds=60, success_criteria=["command exits with code 0"]),
                run=CommandSpec(command=run_command),
                evaluate=CommandSpec(command=eval_command),
                expected={"metric": result.metric, "value": result.expected_value, "tolerance": result.tolerance, "unit": result.unit},
                hardware=paper.hardware.model_copy(),
                config=dict(result.config),
                symbol_mappings=symbol_mappings,
                unmatched_paper_symbols=unmatched_paper,
                unmatched_code_symbols=unmatched_code[:20],
                evidence=evidence,
                risks=risks,
            )
        )
    missing.extend(repo.partial_implementation_notes)
    return experiments, datasets, sorted(set(missing))


def _score(dataset: str | None, metric: str | None, repo: RepoFacts) -> tuple[float, list[EvidenceSpec], list[str]]:
    score = 0.0
    evidence: list[EvidenceSpec] = []
    risks: list[str] = []
    haystack = "\n".join(repo.command_candidates + repo.config_files + repo.readme_commands).lower()
    if dataset and _name_appears_in(dataset, haystack):
        score += 0.25
        evidence.append(
            EvidenceSpec(
                kind="dataset_overlap",
                message=f"Dataset name appears in repository commands or config paths: {dataset}.",
                source_path=_first_source_for_term(dataset, repo),
            )
        )
    elif dataset:
        risks.append(f"Dataset name was not detected in repository commands or config paths: {dataset}.")
    if metric and metric.lower() in haystack:
        score += 0.2
        evidence.append(
            EvidenceSpec(
                kind="metric_overlap",
                message=f"Metric appears near repository instructions: {metric}.",
                source_path=_first_source_for_term(metric, repo),
            )
        )
    elif metric:
        risks.append(f"Metric was not detected in repository instructions: {metric}.")
    if repo.entrypoints.get("train"):
        score += 0.15
        evidence.append(
            EvidenceSpec(kind="entrypoint", message="Training entrypoint detected.", source_path=_script_source(repo.entrypoints["train"][0]))
        )
    if repo.entrypoints.get("evaluate"):
        score += 0.15
        evidence.append(
            EvidenceSpec(
                kind="entrypoint",
                message="Evaluation entrypoint detected.",
                source_path=_script_source(repo.entrypoints["evaluate"][0]),
            )
        )
    if repo.config_files:
        score += 0.1
        evidence.append(EvidenceSpec(kind="config", message="Config files detected.", source_path=repo.config_files[0]))
    if repo.readme_commands:
        score += 0.1
        evidence.append(EvidenceSpec(kind="readme_command", message="README command candidates detected.", source_path="README.md"))
    return min(score, 1.0), evidence, risks


def _best_run_command(dataset: str | None, repo: RepoFacts) -> str | None:
    commands = repo.readme_commands + repo.entrypoints.get("train", [])
    if dataset:
        hit = next((c for c in commands if _name_appears_in(dataset, c)), None)
        if hit:
            return hit
        config_hit = next((c for c in repo.config_files if _name_appears_in(dataset, c)), None)
        if config_hit and repo.entrypoints.get("train"):
            return f"{repo.entrypoints['train'][0]} --config {config_hit}"
    return commands[0] if commands else None


def _best_eval_command(repo: RepoFacts) -> str | None:
    return (repo.entrypoints.get("evaluate") or [None])[0]


def _smoke_command(run_command: str | None, repo: RepoFacts) -> str | None:
    if run_command and run_command.startswith("python "):
        return run_command.split("--config", 1)[0].strip() + " --help"
    train = (repo.entrypoints.get("train") or [None])[0]
    return f"{train} --help" if train else None


SYMBOL_ALIASES: dict[str, tuple[str, ...]] = {
    "alpha": ("alpha", "a"),
    "beta": ("beta", "b"),
    "gamma": ("gamma",),
    "lambda": ("lambda", "lam", "lmbda", "weight_decay", "wd"),
    "lr": ("lr", "learning_rate"),
    "epochs": ("epochs", "num_epochs", "n_epochs"),
    "batch_size": ("batch_size", "bs", "batchsize"),
    "tau": ("tau", "temperature", "temp"),
    "epsilon": ("epsilon", "eps"),
    "momentum": ("momentum",),
    "dropout": ("dropout", "drop_rate"),
}

# Short tokens that would produce too many spurious substring matches.
SHORT_TOKEN_BLOCKLIST = {"a", "b", "c", "x", "y", "z", "i", "j", "k", "n", "m", "lr", "wd", "bs", "eps"}


def _symbol_mapping(
    paper_symbols: list[str], code_symbols: list[str]
) -> tuple[dict[str, str | None], list[str], list[str]]:
    mappings: dict[str, str | None] = {}
    unused_code = set(code_symbols)
    code_norm = {c: _norm(c) for c in code_symbols}
    for symbol in paper_symbols:
        norm = _norm(symbol)
        candidates = SYMBOL_ALIASES.get(norm, (norm,))
        mapped: str | None = None
        for cand in candidates:
            cand_norm = _norm(cand)
            mapped = next((c for c, n in code_norm.items() if n == cand_norm), None)
            if mapped:
                break
        if mapped is None and norm and norm not in SHORT_TOKEN_BLOCKLIST and len(norm) >= 4:
            mapped = next(
                (c for c, n in code_norm.items() if n.startswith(norm) or n.endswith("_" + norm)),
                None,
            )
        mappings[symbol] = mapped
        if mapped in unused_code:
            unused_code.remove(mapped)
    unmatched_paper = [s for s, m in mappings.items() if m is None]
    return mappings, unmatched_paper, sorted(unused_code)


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _name_tokens(value: str) -> list[str]:
    """Split a free-form name like 'C4 (RealNewsLike subset)' into matchable tokens."""
    parts = re.split(r"[^A-Za-z0-9]+", value)
    return [p.lower() for p in parts if p and len(p) >= 2 and p.lower() not in {"the", "and", "for", "with", "set", "subset"}]


def _name_appears_in(name: str, haystack: str) -> bool:
    haystack_norm = _norm(haystack)
    if _norm(name) in haystack_norm:
        return True
    tokens = _name_tokens(name)
    if not tokens:
        return False
    return all(_norm(tok) in haystack_norm for tok in tokens)


def _implementation_status(run_command: str | None, eval_command: str | None, score: float) -> str:
    if not run_command:
        return "missing"
    if not eval_command or score < 0.5:
        return "partial_candidate"
    return "complete_candidate"


def _first_source_for_term(term: str, repo: RepoFacts) -> str | None:
    norm_term = _norm(term)
    for config in repo.config_files:
        if norm_term in _norm(config):
            return config
    for command in repo.readme_commands:
        if norm_term in _norm(command):
            return "README.md"
    return None


def _script_source(command: str) -> str | None:
    for token in command.split():
        if token.endswith(".py") or token.endswith(".sh"):
            return token
    return None


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unknown"
