from pathlib import Path
import subprocess

import yaml
from typer.testing import CliRunner

from paperharness.cli import app


def _build_fixture(tmp_path: Path) -> Path:
    runner = CliRunner()
    output = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "build",
            "--paper",
            "examples/minimal_pytorch/paper.txt",
            "--repo",
            "examples/minimal_pytorch/repo",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    return output


def _front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, raw, _ = text.split("---", 2)
    data = yaml.safe_load(raw)
    assert isinstance(data, dict)
    return data


def test_build_generates_conservative_kit(tmp_path: Path) -> None:
    output = _build_fixture(tmp_path)
    reprokit = (output / "reprokit.yaml").read_text(encoding="utf-8")
    assert "symbol_mappings" in reprokit
    assert "implementation_status" in reprokit
    assert "source_path" in reprokit
    assert (output / "skill" / "scripts" / "repro.py").exists()
    assert (output / "skill" / "references" / "experiment_map.md").exists()


def test_skill_front_matter_is_valid_yaml(tmp_path: Path) -> None:
    top = _front_matter(Path("skills/paperharness/SKILL.md"))
    assert top["name"] == "paperharness"
    assert "description" in top

    output = _build_fixture(tmp_path)
    generated = _front_matter(output / "skill" / "SKILL.md")
    assert generated["name"] == "reproduce-repo"
    assert "description" in generated


def test_generated_repro_cli_inspect_list_report(tmp_path: Path) -> None:
    output = _build_fixture(tmp_path)
    skill_dir = output / "skill"
    for command in (["inspect"], ["list"], ["report"]):
        result = subprocess.run(
            ["python", "scripts/repro.py", *command],
            cwd=skill_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert result.returncode == 0, result.stdout
    assert (skill_dir / "reproducibility_report.md").exists()


def test_prepare_data_missing_command_is_unknown_not_blocked(tmp_path: Path) -> None:
    output = _build_fixture(tmp_path)
    skill_dir = output / "skill"
    result = subprocess.run(
        ["python", "scripts/repro.py", "prepare-data"],
        cwd=skill_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert "data_unknown" in result.stdout
