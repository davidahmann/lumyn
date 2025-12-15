from __future__ import annotations

from pathlib import Path

import typer

from lumyn.store.sqlite import SqliteStore

from ..util import die, resolve_workspace_paths, write_json_to_path_or_stdout
from .init import DEFAULT_POLICY_TEMPLATE, initialize_workspace

app = typer.Typer(help="Show a stored DecisionRecord by decision_id.")


@app.callback(invoke_without_command=True)
def main(
    decision_id: str = typer.Argument(..., help="DecisionRecord decision_id to fetch."),
    *,
    workspace: Path = typer.Option(Path(".lumyn"), "--workspace", help="Workspace directory."),
    out: Path = typer.Option(Path("-"), "--out", help="Output path (or '-' for stdout)."),
    pretty: bool = typer.Option(True, "--pretty/--compact", help="Pretty-print JSON output."),
) -> None:
    paths = resolve_workspace_paths(workspace)
    if not paths.workspace.exists() or not paths.db_path.exists() or not paths.policy_path.exists():
        initialize_workspace(
            workspace=workspace, policy_template=DEFAULT_POLICY_TEMPLATE, force=False
        )

    store = SqliteStore(paths.db_path)
    record = store.get_decision_record(decision_id)
    if record is None:
        die(f"decision not found: {decision_id}")

    write_json_to_path_or_stdout(record, path=out, pretty=pretty)
