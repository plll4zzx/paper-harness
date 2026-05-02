from pathlib import Path

from typer.testing import CliRunner

from paperharness.cli import app


def test_build_generates_conservative_kit(tmp_path: Path) -> None:
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
    reprokit = (output / "reprokit.yaml").read_text(encoding="utf-8")
    assert "symbol_mappings" in reprokit
    assert "implementation_status" in reprokit
    assert (output / "skill" / "scripts" / "repro.py").exists()
    assert (output / "skill" / "references" / "experiment_map.md").exists()
