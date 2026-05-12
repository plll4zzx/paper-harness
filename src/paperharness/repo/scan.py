from __future__ import annotations

import ast
import re
from pathlib import Path

from paperharness.ir.schema import RepoEnvironment, RepoFacts


COMMAND_RE = re.compile(r"^(?:python|pip|conda|bash|sh|make)\s+.+$")


def scan_repo(repo_path: Path) -> RepoFacts:
    files = {p.relative_to(repo_path).as_posix(): p for p in repo_path.rglob("*") if p.is_file()}
    env_files = {
        "requirements": "requirements.txt" if "requirements.txt" in files else None,
        "conda": "environment.yml" if "environment.yml" in files else None,
        "dockerfile": "Dockerfile" if "Dockerfile" in files else None,
        "pyproject": "pyproject.toml" if "pyproject.toml" in files else None,
    }
    install_commands: list[str] = []
    if env_files["requirements"]:
        install_commands.append("pip install -r requirements.txt")
    if env_files["conda"]:
        install_commands.append("conda env create -f environment.yml")
    if env_files["pyproject"]:
        install_commands.append("pip install -e .")

    readme_commands = _readme_commands(files)
    scripts = _script_files(files)
    configs = _config_files(files)
    entrypoints = {
        "setup": install_commands[:],
        "train": _entrypoint_commands(
            files,
            exact=["train.py", "main.py", "finetune.py", "fit.py", "launch.py", "run.py", "pretrain.py"],
            patterns=["train_*.py", "finetune_*.py", "pretrain_*.py"],
            readme_commands=readme_commands,
        ),
        "evaluate": _entrypoint_commands(
            files,
            exact=["eval.py", "evaluate.py", "inference.py", "predict.py", "test.py", "benchmark.py"],
            patterns=["eval_*.py", "evaluate_*.py", "test_*.py", "benchmark_*.py", "attack_*.py"],
            readme_commands=readme_commands,
        ),
        "data": _entrypoint_commands(
            files,
            exact=["prepare_data.py", "download.py"],
            patterns=["collect_*.py", "prepare_*.py", "preprocess_*.py", "download_*.py"],
            readme_commands=readme_commands,
        ),
        "test": _entrypoint_commands(files, exact=["pytest.ini", "tox.ini"], patterns=[], readme_commands=readme_commands),
        "scripts": [f"bash {s}" if s.endswith(".sh") else f"python {s}" for s in scripts],
    }
    command_candidates = sorted(set(readme_commands + install_commands + sum(entrypoints.values(), [])))
    code_symbols = _code_symbols(repo_path, files)
    frameworks = _framework_candidates(repo_path, files)
    partial_notes = []
    if not entrypoints["train"]:
        partial_notes.append("No train entrypoint detected; some paper experiments may not be implemented.")
    if not entrypoints["evaluate"]:
        partial_notes.append("No evaluation entrypoint detected; reported paper metrics may require manual extraction.")
    if not configs:
        partial_notes.append("No config files detected; hyperparameter mapping may be incomplete.")
    return RepoFacts(
        language="python" if any(name.endswith(".py") for name in files) else "unknown",
        framework_candidates=frameworks,
        environment=RepoEnvironment(type="python", install_commands=install_commands, files=env_files),
        entrypoints=entrypoints,
        command_candidates=command_candidates,
        config_files=configs,
        code_symbols=code_symbols,
        readme_commands=readme_commands,
        partial_implementation_notes=partial_notes,
    )


SCRIPT_DIRS = ("scripts/", "tools/", "bin/", "experiments/", "examples/")
CONFIG_DIRS = ("configs/", "config/", "conf/", "hydra/", "yaml/")
CONFIG_EXTS = (".yaml", ".yml", ".json", ".toml")


def _script_files(files: dict[str, Path]) -> list[str]:
    return sorted(
        name for name in files
        if name.endswith((".sh", ".py"))
        and (
            any(name.startswith(d) for d in SCRIPT_DIRS)
            or "/" not in name and name.endswith(".sh")
        )
    )


def _config_files(files: dict[str, Path]) -> list[str]:
    out: set[str] = set()
    for name in files:
        if not name.endswith(CONFIG_EXTS):
            continue
        if any(name.startswith(d) for d in CONFIG_DIRS):
            out.add(name)
            continue
        # Top-level configs that are commonly experiment knobs.
        if "/" not in name and name not in {"pyproject.toml", "package.json"}:
            out.add(name)
    return sorted(out)


def _readme_commands(files: dict[str, Path]) -> list[str]:
    readme = next((files[n] for n in files if n.lower() == "readme.md"), None)
    if not readme:
        return []
    text = readme.read_text(encoding="utf-8", errors="ignore")
    commands = []
    for line in text.splitlines():
        stripped = line.strip().lstrip("$ ").rstrip(".")
        if COMMAND_RE.match(stripped):
            commands.append(stripped)
    return sorted(set(commands))


def _entrypoint_commands(
    files: dict[str, Path],
    exact: list[str],
    patterns: list[str],
    readme_commands: list[str],
) -> list[str]:
    import fnmatch

    found: set[str] = set()
    matched_names: set[str] = set()
    for name in files:
        basename = name.rsplit("/", 1)[-1]
        if basename in exact:
            found.add(f"python {name}")
            matched_names.add(basename)
            continue
        for pattern in patterns:
            if fnmatch.fnmatchcase(basename, pattern):
                found.add(f"python {name}")
                matched_names.add(basename)
                break
    for command in readme_commands:
        if any(n in command for n in matched_names | set(exact)):
            found.add(command)
    return sorted(found)


MAX_CODE_SYMBOLS = 400

HYPERPARAM_NAME_HINTS = (
    "lr", "learning_rate", "epoch", "batch", "weight_decay", "momentum",
    "dropout", "temperature", "tau", "alpha", "beta", "gamma", "lambda",
    "lam", "eps", "epsilon", "seed", "num_", "n_", "hidden", "dim",
    "depth", "layers", "heads", "warmup", "decay", "optimizer", "scheduler",
)


def _code_symbols(repo_path: Path, files: dict[str, Path]) -> list[str]:
    """Surface symbols *likely* relevant to paper-to-code variable mapping.

    Sources:

    1. CLI flags from argparse / click / typer (``add_argument("--lr")`` etc.) —
       always kept, because they are explicitly declared as knobs.
    2. Module-level constants whose names look like hyperparameters (filtered).
    3. Keys from any YAML/JSON/TOML config in the repo (filtered).
    4. Top-level keys of YAML/JSON config files — always kept.
    """
    cli_flags: set[str] = set()
    other_constants: set[str] = set()
    config_keys: set[str] = set()
    for name, path in files.items():
        if name.endswith(".py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError:
                continue
            cli_flags.update(_argparse_flags(tree))
            other_constants.update(_module_level_constants(tree))
        elif name.endswith((".yaml", ".yml")):
            config_keys.update(_yaml_hyperparam_keys(path))

    # CLI flags and config keys are always kept; other constants are filtered by hint.
    kept = set(cli_flags) | set(config_keys) | {s for s in other_constants if _looks_like_hyperparam(s)}
    return sorted(kept)[:MAX_CODE_SYMBOLS]


def _argparse_flags(tree: ast.AST) -> set[str]:
    flags: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.attr if isinstance(func, ast.Attribute)
            else func.id if isinstance(func, ast.Name)
            else None
        )
        if name not in {"add_argument", "option", "argument"}:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                token = arg.value.lstrip("-").replace("-", "_")
                if token:
                    flags.add(token)
                break
    return flags


def _module_level_constants(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    if not isinstance(tree, ast.Module):
        return names
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _yaml_hyperparam_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return keys
    for line in text.splitlines():
        stripped = line.strip()
        if ":" not in stripped or stripped.startswith("#"):
            continue
        key = stripped.split(":", 1)[0].strip().strip("'\"")
        if key and key.replace("_", "").replace("-", "").isalnum():
            keys.add(key.replace("-", "_"))
    return keys


def _looks_like_hyperparam(symbol: str) -> bool:
    if len(symbol) < 2 or len(symbol) > 40:
        return False
    lowered = symbol.lower()
    return any(hint in lowered for hint in HYPERPARAM_NAME_HINTS)


def _framework_candidates(repo_path: Path, files: dict[str, Path]) -> list[str]:
    text = ""
    for name in ("requirements.txt", "pyproject.toml", "environment.yml", "README.md"):
        path = files.get(name)
        if path:
            text += "\n" + path.read_text(encoding="utf-8", errors="ignore").lower()
    frameworks = []
    for candidate in ("pytorch", "torch", "tensorflow", "jax", "transformers", "huggingface"):
        if candidate in text:
            frameworks.append("pytorch" if candidate == "torch" else candidate)
    return sorted(set(frameworks))
