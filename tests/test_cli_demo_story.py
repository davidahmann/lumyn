from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app


def test_cli_demo_story_runs(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    result = runner.invoke(app, ["demo", "--workspace", str(workspace), "--story"])
    assert result.exit_code == 0
    assert "Lumyn demo story" in result.stdout
    assert "1) Decide on a refund request" in result.stdout
    assert "2) Label the outcome as a failure" in result.stdout
    assert "3) Re-run a similar decision" in result.stdout
    assert result.stdout.count("decision_id:") == 2
    assert result.stdout.count("verdict:") == 2
