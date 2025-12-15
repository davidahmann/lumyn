from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app


def test_cli_doctor_fix_creates_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    result = runner.invoke(app, ["doctor", "--workspace", str(workspace), "--fix"])
    assert result.exit_code == 0
    assert "ok" in result.stdout
    assert (workspace / "policy.yml").exists()
    assert (workspace / "lumyn.db").exists()
