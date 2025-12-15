from __future__ import annotations

from pathlib import Path

import typer

from lumyn.policy.loader import load_policy
from lumyn.store.sqlite import SqliteStore

from ..util import die, resolve_workspace_paths
from .init import DEFAULT_POLICY_TEMPLATE, initialize_workspace

app = typer.Typer(help="Check local workspace health.")


@app.callback(invoke_without_command=True)
def main(
    *,
    workspace: Path = typer.Option(Path(".lumyn"), "--workspace", help="Workspace directory."),
    fix: bool = typer.Option(
        False, "--fix", help="Create/repair missing workspace files (policy + db)."
    ),
    policy_template: Path = typer.Option(
        DEFAULT_POLICY_TEMPLATE,
        "--policy-template",
        help="Policy template to copy if policy.yml is missing.",
    ),
) -> None:
    paths = resolve_workspace_paths(workspace)
    if fix:
        initialize_workspace(workspace=workspace, policy_template=policy_template, force=False)

    if not paths.workspace.exists():
        die(f"workspace not found: {paths.workspace}")

    if not paths.policy_path.exists():
        die(f"policy not found: {paths.policy_path}")

    if not paths.db_path.exists():
        die(f"db not found: {paths.db_path}")

    loaded = load_policy(paths.policy_path)
    store = SqliteStore(paths.db_path)
    store.init()
    stats = store.get_stats()

    typer.echo("ok")
    typer.echo(f"workspace: {paths.workspace}")
    typer.echo(f"policy_hash: {loaded.policy_hash}")
    typer.echo(f"decisions: {stats.decisions}")
    typer.echo(f"decision_events: {stats.decision_events}")
    typer.echo(f"memory_items: {stats.memory_items}")
    typer.echo(f"policy_snapshots: {stats.policy_snapshots}")
