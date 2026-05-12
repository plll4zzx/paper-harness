from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ExperimentStatus = Literal[
    "unmapped",
    "mapped",
    "setup_ready",
    "data_ready",
    "smoke_passed",
    "running",
    "evaluated",
    "reported",
    "blocked",
    "failed",
]


class CommandSpec(BaseModel):
    command: str | None = None
    expected_outputs: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = None
    success_criteria: list[str] = Field(default_factory=list)
    source: Literal["repo", "paper", "manual"] = "repo"
    source_span: str | None = None


class HardwareSpec(BaseModel):
    gpu_required: bool = False
    min_gpu_memory_gb: float | None = None
    notes: str | None = None


class PaperResult(BaseModel):
    id: str
    label: str
    description: str | None = None
    dataset: str | None = None
    metric: str | None = None
    expected_value: float | str | None = None
    tolerance: float | None = None
    unit: str | None = None
    symbols: list[str] = Field(default_factory=list)
    config: dict[str, str | float | int | bool | None] = Field(default_factory=dict)
    confidence: float = 0.0
    source_span: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class PaperFacts(BaseModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    main_claims: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    results: list[PaperResult] = Field(default_factory=list)
    hardware: HardwareSpec = Field(default_factory=HardwareSpec)
    extraction_method: Literal["regex", "llm", "marker+regex"] = "regex"
    source_format: Literal["pdf", "markdown", "text"] = "text"


class RepoEnvironment(BaseModel):
    type: str = "unknown"
    python_version: str | None = None
    install_commands: list[str] = Field(default_factory=list)
    files: dict[str, str | None] = Field(default_factory=dict)


class RepoFacts(BaseModel):
    language: str = "unknown"
    framework_candidates: list[str] = Field(default_factory=list)
    environment: RepoEnvironment = Field(default_factory=RepoEnvironment)
    entrypoints: dict[str, list[str]] = Field(default_factory=dict)
    command_candidates: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    code_symbols: list[str] = Field(default_factory=list)
    readme_commands: list[str] = Field(default_factory=list)
    partial_implementation_notes: list[str] = Field(default_factory=list)


class DatasetSpec(BaseModel):
    id: str
    name: str
    source: str | None = None
    prepare_command: str | None = None
    status: str = "unknown"
    notes: list[str] = Field(default_factory=list)


class ExpectedSpec(BaseModel):
    metric: str | None = None
    value: float | str | None = None
    tolerance: float | None = None
    unit: str | None = None


class EvidenceSpec(BaseModel):
    kind: str = "heuristic"
    message: str
    source_path: str | None = None


class ReviewRequiredSpec(BaseModel):
    experiment_id: str
    issue_type: str
    symbols: list[str] = Field(default_factory=list)
    severity: str = "review"
    message: str


class ExperimentSpec(BaseModel):
    id: str
    paper_result_id: str | None = None
    title: str
    status: ExperimentStatus = "unmapped"
    confidence: float = 0.0
    implementation_status: Literal["complete_candidate", "partial_candidate", "missing", "unknown"] = "unknown"
    depends_on: list[str] = Field(default_factory=list)
    setup: CommandSpec = Field(default_factory=CommandSpec)
    data: CommandSpec = Field(default_factory=CommandSpec)
    smoke: CommandSpec = Field(default_factory=CommandSpec)
    run: CommandSpec = Field(default_factory=CommandSpec)
    evaluate: CommandSpec = Field(default_factory=CommandSpec)
    hardware: HardwareSpec = Field(default_factory=HardwareSpec)
    expected: ExpectedSpec = Field(default_factory=ExpectedSpec)
    config: dict[str, str | float | int | bool | None] = Field(default_factory=dict)
    symbol_mappings: dict[str, str | None] = Field(default_factory=dict)
    unmatched_paper_symbols: list[str] = Field(default_factory=list)
    unmatched_code_symbols: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSpec] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ProjectSpec(BaseModel):
    name: str
    repo_url: str | None = None
    repo_path: str | None = None
    repo_commit: str | None = None
    paper_path: str | None = None
    output_dir: str = "./paperharness-output"


class ReportingSpec(BaseModel):
    required_sections: list[str] = Field(
        default_factory=lambda: [
            "Summary",
            "Environment",
            "Commands",
            "Datasets",
            "Results",
            "Comparison with paper",
            "Symbol and variable mapping",
            "Missing information",
            "Failure modes",
            "Conclusion",
        ]
    )


class ReproKit(BaseModel):
    schema_version: str = "0.1"
    project: ProjectSpec
    paper: PaperFacts = Field(default_factory=PaperFacts)
    repo: RepoFacts = Field(default_factory=RepoFacts)
    datasets: list[DatasetSpec] = Field(default_factory=list)
    experiments: list[ExperimentSpec] = Field(default_factory=list)
    reporting: ReportingSpec = Field(default_factory=ReportingSpec)
    state: dict[str, Any] = Field(default_factory=dict)
    missing_info: list[str] = Field(default_factory=list)
    review_required: list[ReviewRequiredSpec] = Field(default_factory=list)
