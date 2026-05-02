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
    scripts = sorted([name for name in files if name.startswith("scripts/") and name.endswith((".sh", ".py"))])
    configs = sorted([name for name in files if name.startswith("configs/") and name.endswith((".yaml", ".yml", ".json"))])
    entrypoints = {
        "setup": install_commands[:],
        "train": _entrypoint_commands(files, ["train.py", "main.py"], readme_commands),
        "evaluate": _entrypoint_commands(files, ["eval.py", "evaluate.py"], readme_commands),
        "test": _entrypoint_commands(files, ["test.py"], readme_commands),
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


def _entrypoint_commands(files: dict[str, Path], names: list[str], readme_commands: list[str]) -> list[str]:
    found = []
    for name in names:
        if name in files:
            found.append(f"python {name}")
    for command in readme_commands:
        if any(name in command for name in names):
            found.append(command)
    return sorted(set(found))


def _code_symbols(repo_path: Path, files: dict[str, Path]) -> list[str]:
    symbols: set[str] = set()
    for name, path in files.items():
        if not name.endswith(".py"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.add(node.name)
            elif isinstance(node, ast.arg):
                symbols.add(node.arg)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                symbols.add(node.id)
    return sorted(s for s in symbols if len(s) > 1)


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
