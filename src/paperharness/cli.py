from __future__ import annotations

import json
from pathlib import Path
import shutil

import typer
from rich.console import Console

from paperharness.generate.kit import generate_kit
from paperharness.ir.io import read_yaml, write_yaml
from paperharness.ir.schema import ProjectSpec, ReproKit, ReviewRequiredSpec
from paperharness.ir.validate import validate_output
from paperharness.matcher.match import build_experiments
from paperharness.paper import llm_extract
from paperharness.paper.parse import load_source, parse_paper
from paperharness.repo.clone import looks_like_url, resolve_repo
from paperharness.repo.scan import scan_repo

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def build(
    paper: Path = typer.Option(..., "--paper", exists=True, readable=True),
    repo: str = typer.Option(..., "--repo", help="Local path OR GitHub URL (https/git/ssh) OR 'owner/repo'."),
    output: Path = typer.Option(Path("paperharness-output"), "--out", "--output"),
    force: bool = typer.Option(False, "--force", help="Replace an existing generated output directory."),
    extraction: Path | None = typer.Option(
        None,
        "--extraction",
        exists=True,
        readable=True,
        help="JSON file produced by an LLM-driven extraction step (paperharness extract-text emits the prompt).",
    ),
    grobid_url: str | None = typer.Option(
        None,
        "--grobid-url",
        help="GROBID service URL (overrides $GROBID_URL). Used for structured title/abstract/sections.",
    ),
) -> None:
    """Run the full PaperHarness MVP pipeline."""
    if looks_like_url(repo):
        console.print(f"[cyan]Cloning[/cyan] {repo} (shallow)...")
    try:
        repo_path = resolve_repo(repo)
    except (FileNotFoundError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    _prepare_output_dir(output, paper, repo_path, force)
    extraction_payload = llm_extract.load_extraction(extraction) if extraction else None
    paper_facts = parse_paper(paper, extraction=extraction_payload, grobid_url=grobid_url)
    repo_facts = scan_repo(repo_path)
    experiments, datasets, missing = build_experiments(paper_facts, repo_facts)
    if extraction_payload:
        attach_log = llm_extract.attach_reproduction_commands(experiments, repo_facts, extraction_payload)
        for line in attach_log:
            console.print(f"[cyan]LLM-cmd[/cyan] {line}")
    review_required = _review_required(experiments)
    review_required.extend(llm_extract.review_items_from_facts(paper_facts))
    kit = ReproKit(
        project=ProjectSpec(
            name=repo_path.name,
            repo_url=repo if looks_like_url(repo) else None,
            repo_path=str(repo_path),
            paper_path=str(paper.resolve()),
            output_dir=str(output.resolve()),
        ),
        paper=paper_facts,
        repo=repo_facts,
        datasets=datasets,
        experiments=experiments,
        missing_info=missing,
        review_required=review_required,
        state={"experiments": {exp.id: {"status": "not_started", "logs": [], "artifacts": []} for exp in experiments}},
    )
    generate_kit(kit, output)
    if not _print_validation(output):
        raise typer.Exit(1)


@app.command("analyze-paper")
def analyze_paper(paper: Path = typer.Argument(..., exists=True, readable=True), output: Path | None = None) -> None:
    """Analyze a paper PDF, markdown, or text file."""
    facts = parse_paper(paper)
    if output:
        write_yaml(output, facts.model_dump(mode="json"))
    console.print_json(data=facts.model_dump(mode="json"))


@app.command("fetch")
def fetch_paper(
    target: str = typer.Argument(..., help="arXiv ID (e.g. '2509.09112' or 'arxiv:2509.09112'), arXiv abs/pdf URL, or any HTTPS PDF URL."),
    output: Path = typer.Option(Path("paper.pdf"), "--out", "--output"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Download a paper PDF locally so it can be fed to extract-text / build."""
    import re
    from urllib.request import Request, urlopen

    if output.exists() and not force:
        raise typer.BadParameter(f"output file exists: {output}. Pass --force to overwrite.")

    url = target
    arxiv_match = re.fullmatch(r"(?:arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?)", target, flags=re.IGNORECASE)
    if arxiv_match:
        url = f"https://arxiv.org/pdf/{arxiv_match.group(1)}"
    elif "arxiv.org/abs/" in target:
        url = target.replace("/abs/", "/pdf/")

    console.print(f"[cyan]Fetching[/cyan] {url}")
    request = Request(url, headers={"User-Agent": "paperharness-fetch/0.1"})
    try:
        with urlopen(request, timeout=60) as response:
            output.write_bytes(response.read())
    except Exception as exc:
        raise typer.BadParameter(f"download failed: {exc}") from exc
    console.print(f"[green]OK[/green] saved to {output} ({output.stat().st_size} bytes)")


@app.command("extract-text")
def extract_text_command(
    paper: Path = typer.Argument(..., exists=True, readable=True),
    out_dir: Path = typer.Option(Path("paperharness-extract"), "--out", "--output"),
    grobid_url: str | None = typer.Option(None, "--grobid-url"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Convert a paper to markdown (via Marker if installed) + GROBID sections + an LLM extraction prompt.

    The next step is for the calling agent to read extraction_prompt.md, produce a JSON object that
    validates against extraction_schema.json, save it as extraction.json, then invoke:

        paperharness build --paper ... --repo ... --extraction <out_dir>/extraction.json
    """
    if out_dir.exists():
        if not force:
            raise typer.BadParameter(f"output directory already exists: {out_dir}. Pass --force to replace it.")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    source = load_source(paper, grobid_url=grobid_url)
    paper_md = out_dir / "paper.md"
    paper_md.write_text(source.text, encoding="utf-8")

    grobid_path = out_dir / "paper.sections.json"
    if source.grobid:
        grobid_path.write_text(json.dumps(source.grobid.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    schema_path = out_dir / "extraction_schema.json"
    schema_path.write_text(json.dumps(llm_extract.EXTRACTION_SCHEMA, indent=2), encoding="utf-8")

    prompt = llm_extract.build_extraction_prompt(
        source.text,
        grobid_sections=source.grobid.to_dict() if source.grobid else None,
    )
    prompt_path = out_dir / "extraction_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    console.print(f"[green]OK[/green] paper text written to {paper_md} (format={source.source_format}, marker={source.used_marker})")
    if paper.suffix.lower() == ".pdf" and not source.used_marker:
        console.print(
            "[yellow]WARN[/yellow] Marker is not installed, so the PDF was extracted with PyMuPDF. "
            "Double-column papers, tables, and equations may lose structure. "
            r"Strongly recommended: [bold]pip install 'paperharness\[parse]'[/bold] and rerun extract-text."
        )
    if source.grobid:
        console.print(f"[green]OK[/green] GROBID sections written to {grobid_path}")
    elif paper.suffix.lower() == ".pdf":
        console.print("[yellow]WARN[/yellow] GROBID not used (set --grobid-url or $GROBID_URL to enable structural cross-check)")
    console.print(f"[green]OK[/green] extraction prompt written to {prompt_path}")
    console.print(f"[green]OK[/green] extraction schema written to {schema_path}")
    console.print(
        "\nNext step: an agent should read the prompt, emit JSON conforming to the schema, "
        f"save it as {out_dir / 'extraction.json'}, then run `paperharness build --extraction <that file>`."
    )


@app.command("analyze-repo")
def analyze_repo(repo: Path = typer.Argument(..., exists=True, file_okay=False, readable=True), output: Path | None = None) -> None:
    """Analyze a local repository."""
    facts = scan_repo(repo)
    if output:
        write_yaml(output, facts.model_dump(mode="json"))
    console.print_json(data=facts.model_dump(mode="json"))


@app.command()
def generate(
    ir: Path = typer.Option(..., "--ir", exists=True, readable=True),
    output: Path = typer.Option(Path("paperharness-output"), "--out", "--output"),
    force: bool = typer.Option(False, "--force", help="Replace an existing generated output directory."),
) -> None:
    """Generate kit files from reprokit.yaml."""
    kit = read_yaml(ir)
    paper = Path(kit.project.paper_path) if kit.project.paper_path else None
    repo = Path(kit.project.repo_path) if kit.project.repo_path else None
    _prepare_output_dir(output, paper, repo, force)
    kit.project.output_dir = str(output.resolve())
    generate_kit(kit, output)
    console.print(f"Generated kit at {output}")


def _print_validation(output_dir: Path) -> bool:
    ok, warnings, errors = validate_output(output_dir)
    for item in ok:
        console.print(f"[green]OK[/green] {item}")
    for item in warnings:
        console.print(f"[yellow]WARN[/yellow] {item}")
    for item in errors:
        console.print(f"[red]ERR[/red] {item}")
    return not errors


@app.command()
def validate(output_dir: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """Validate a generated kit directory."""
    if not _print_validation(output_dir):
        raise typer.Exit(1)


@app.command("validate-ir")
def validate_ir(ir: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Validate reprokit.yaml structure."""
    read_yaml(ir)
    console.print("[green]OK[/green] IR is structurally valid")


SUPPORTED_EXPORT_TARGETS = {"codex", "claude-code", "opencode"}


@app.command()
def export(
    output_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    target: str = typer.Option("codex", "--target"),
) -> None:
    """Validate an exported kit for a target agent format."""
    if target not in SUPPORTED_EXPORT_TARGETS:
        console.print(
            f"[yellow]WARN[/yellow] export target '{target}' has no dedicated adapter yet; "
            f"falling back to generic kit validation. Known targets: {sorted(SUPPORTED_EXPORT_TARGETS)}"
        )
    if not _print_validation(output_dir):
        raise typer.Exit(1)


def _prepare_output_dir(output: Path, paper: Path | None, repo: Path | None, force: bool) -> None:
    output_resolved = output.resolve()
    protected = [path.resolve() for path in (paper, repo) if path is not None and path.exists()]
    if any(output_resolved == path or _is_relative_to(path, output_resolved) or _is_relative_to(output_resolved, path) for path in protected):
        raise typer.BadParameter("output directory must not be the paper path, the repo path, or inside/around either source")
    if output.exists():
        if not force:
            raise typer.BadParameter(f"output directory already exists: {output}. Pass --force to replace it.")
        if not output.is_dir():
            raise typer.BadParameter(f"output path exists and is not a directory: {output}")
        shutil.rmtree(output)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _review_required(experiments) -> list[ReviewRequiredSpec]:
    items: list[ReviewRequiredSpec] = []
    for exp in experiments:
        # Filter out anything that looks like "key=value" or has spaces — those are config
        # overrides that ended up in the symbols field by accident and should not fire a
        # variable-mapping review item.
        bare = [s for s in exp.unmatched_paper_symbols if "=" not in s and " " not in s]
        if bare:
            items.append(
                ReviewRequiredSpec(
                    experiment_id=exp.id,
                    issue_type="unmatched_paper_symbols",
                    symbols=bare,
                    severity="review",
                    message="Paper symbols do not map cleanly to detected code variables.",
                )
            )
    return items


if __name__ == "__main__":
    app()
