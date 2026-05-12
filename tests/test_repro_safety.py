from __future__ import annotations

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from paperharness.cli import app


def _build(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "build",
            "--paper", "examples/minimal_pytorch/paper.txt",
            "--repo", "examples/minimal_pytorch/repo",
            "--out", str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    return out


def test_smoke_continues_on_failure(tmp_path: Path) -> None:
    out = _build(tmp_path)
    # The kit's smoke command exists for the example. Run it with --dry-run so we never
    # actually execute anything, and verify the runner returns successfully.
    result = subprocess.run(
        ["python", "scripts/repro.py", "smoke", "--dry-run"],
        cwd=out / "skill",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert "dry-run" in result.stdout.lower() or "executed=False" in result.stdout


def test_dangerous_command_is_refused_without_yes(tmp_path: Path) -> None:
    out = _build(tmp_path)
    kit_path = out / "reprokit.yaml"
    text = kit_path.read_text(encoding="utf-8")
    # Inject a destructive command into setup; verify setup refuses without --yes.
    text = text.replace(
        "pip install -r requirements.txt",
        "rm -rf /tmp/paperharness-evil-test",
    )
    kit_path.write_text(text, encoding="utf-8")
    (out / "skill" / "reprokit.yaml").write_text(text, encoding="utf-8")
    result = subprocess.run(
        ["python", "scripts/repro.py", "setup"],
        cwd=out / "skill",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode != 0
    assert "destructive-looking" in result.stdout
