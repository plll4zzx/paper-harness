from pathlib import Path

from typer.testing import CliRunner

from paperharness.cli import app


def test_validate_generated_output(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "out"
    build = runner.invoke(
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
    assert build.exit_code == 0, build.output
    validate = runner.invoke(app, ["validate", str(output)])
    assert validate.exit_code == 0, validate.output
