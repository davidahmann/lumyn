from __future__ import annotations

from pathlib import Path

import typer

from lumyn.policy.loader import read_policy_text
from lumyn.store.sqlite import SqliteStore

from ..util import die, resolve_workspace_paths

app = typer.Typer(help="Initialize a local Lumyn workspace.")

DEFAULT_POLICY_TEMPLATE = Path("policies/starter.v1.yml")


def initialize_workspace(*, workspace: Path, policy_template: Path, force: bool) -> None:
    paths = resolve_workspace_paths(workspace)
    paths.workspace.mkdir(parents=True, exist_ok=True)

    if paths.policy_path.exists() and not force:
        pass
    else:
        try:
            policy_text = read_policy_text(policy_template)
        except FileNotFoundError:
            die(f"policy template not found: {policy_template}")
        paths.policy_path.write_text(policy_text, encoding="utf-8")

    store = SqliteStore(paths.db_path)
    store.init()


@app.callback(invoke_without_command=True)
def main(
    *,
    workspace: Path = typer.Option(
        Path(".lumyn"),
        "--workspace",
        help="Workspace directory to create/use.",
    ),
    policy_template: Path = typer.Option(
        DEFAULT_POLICY_TEMPLATE,
        "--policy-template",
        help="Policy template to copy into the workspace.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing policy.yml."),
) -> None:
    initialize_workspace(workspace=workspace, policy_template=policy_template, force=force)

    paths = resolve_workspace_paths(workspace)
    typer.echo(f"workspace: {paths.workspace}")
    typer.echo(f"policy: {paths.policy_path}")
    typer.echo(f"db: {paths.db_path}")
