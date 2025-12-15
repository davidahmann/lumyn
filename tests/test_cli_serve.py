from __future__ import annotations

from typer.testing import CliRunner

from lumyn.cli.main import app


def test_cli_serve_dry_run() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--dry-run"])
    assert result.exit_code == 0
    assert "Lumyn service" in result.stdout
    assert "uvicorn --factory lumyn.api.app:create_app" in result.stdout
