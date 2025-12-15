from __future__ import annotations

from pathlib import Path

import typer

from lumyn.policy.loader import load_policy

from ..util import die, resolve_workspace_paths

app = typer.Typer(help="Policy utilities.")


@app.command("validate")
def validate(
    *,
    workspace: Path = typer.Option(Path(".lumyn"), "--workspace", help="Workspace directory."),
    path: Path | None = typer.Option(
        None,
        "--path",
        help="Policy path (defaults to workspace policy.yml).",
    ),
) -> None:
    paths = resolve_workspace_paths(workspace)
    policy_path = path or paths.policy_path
    if not policy_path.exists():
        die(f"policy not found: {policy_path}")

    loaded = load_policy(policy_path)
    typer.echo("ok")
    typer.echo(f"policy_id: {loaded.policy['policy_id']}")
    typer.echo(f"policy_version: {loaded.policy['policy_version']}")
    typer.echo(f"policy_hash: {loaded.policy_hash}")
