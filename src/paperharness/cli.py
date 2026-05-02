from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from paperharness.generate.kit import generate_kit
from paperharness.ir.io import read_yaml, write_yaml
from paperharness.ir.schema import ProjectSpec, ReproKit
from paperharness.ir.validate import validate_output
from paperharness.matcher.match import build_experiments
from paperharness.paper.parse import parse_paper
from paperharness.repo.scan import scan_repo

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def build(
    paper: Path = typer.Option(..., "--paper", exists=True, readable=True),
    repo: Path = typer.Option(..., "--repo", exists=True, file_okay=False, readable=True),
    output: Path = typer.Option(Path("paperharness-output"), "--output"),
) -> None:
    """Run the full PaperHarness MVP pipeline."""
    paper_facts = parse_paper(paper)
    repo_facts = scan_repo(repo)
    experiments, datasets, missing = build_experiments(paper_facts, repo_facts)
    kit = ReproKit(
        project=ProjectSpec(
            name=repo.resolve().name,
            repo_path=str(repo.resolve()),
            paper_path=str(paper.resolve()),
            output_dir=str(output.resolve()),
        ),
        paper=paper_facts,
        repo=repo_facts,
        datasets=datasets,
        experiments=experiments,
        missing_info=missing,
        state={"experiments": {exp.id: {"status": "not_started", "logs": [], "artifacts": []} for exp in experiments}},
    )
    generate_kit(kit, output)
    ok, warnings, errors = validate_output(output)
    for item in ok:
        console.print(f"[green]OK[/green] {item}")
    for item in warnings:
        console.print(f"[yellow]WARN[/yellow] {item}")
    for item in errors:
        console.print(f"[red]ERR[/red] {item}")
    if errors:
        raise typer.Exit(1)


@app.command("analyze-paper")
def analyze_paper(paper: Path = typer.Argument(..., exists=True, readable=True), output: Path | None = None) -> None:
    """Analyze a paper PDF, markdown, or text file."""
    facts = parse_paper(paper)
    if output:
        write_yaml(output, facts.model_dump(mode="json"))
    console.print_json(data=facts.model_dump(mode="json"))


@app.command("analyze-repo")
def analyze_repo(repo: Path = typer.Argument(..., exists=True, file_okay=False, readable=True), output: Path | None = None) -> None:
    """Analyze a local repository."""
    facts = scan_repo(repo)
    if output:
        write_yaml(output, facts.model_dump(mode="json"))
    console.print_json(data=facts.model_dump(mode="json"))


@app.command()
def generate(ir: Path = typer.Option(..., "--ir", exists=True, readable=True), output: Path = typer.Option(Path("paperharness-output"), "--output")) -> None:
    """Generate kit files from reprokit.yaml."""
    generate_kit(read_yaml(ir), output)
    console.print(f"Generated kit at {output}")


@app.command()
def validate(output_dir: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """Validate a generated kit directory."""
    ok, warnings, errors = validate_output(output_dir)
    for item in ok:
        console.print(f"[green]OK[/green] {item}")
    for item in warnings:
        console.print(f"[yellow]WARN[/yellow] {item}")
    for item in errors:
        console.print(f"[red]ERR[/red] {item}")
    if errors:
        raise typer.Exit(1)


@app.command("validate-ir")
def validate_ir(ir: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Validate reprokit.yaml structure."""
    read_yaml(ir)
    console.print("[green]OK[/green] IR is structurally valid")


@app.command()
def export(output_dir: Path = typer.Argument(..., exists=True, file_okay=False), target: str = typer.Option("codex", "--target")) -> None:
    """Validate an exported kit for a target agent format."""
    if target != "codex":
        console.print(f"[yellow]WARN[/yellow] only codex export validation is implemented; got {target}")
    validate(output_dir)


if __name__ == "__main__":
    app()
