from __future__ import annotations

from pathlib import Path

import typer

from lumyn.core.decide import LumynConfig, decide

from ..util import (
    read_json_from_path_or_stdin,
    resolve_workspace_paths,
    write_json_to_path_or_stdout,
)
from .init import DEFAULT_POLICY_TEMPLATE, initialize_workspace

app = typer.Typer(help="Evaluate a DecisionRequest and emit a DecisionRecord.")


@app.callback(invoke_without_command=True)
def main(
    *,
    workspace: Path = typer.Option(Path(".lumyn"), "--workspace", help="Workspace directory."),
    input_path: Path = typer.Argument(
        Path("-"),
        help="DecisionRequest JSON path (or '-' for stdin).",
    ),
    out: Path = typer.Option(Path("-"), "--out", help="Output path (or '-' for stdout)."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    paths = resolve_workspace_paths(workspace)
    if not paths.workspace.exists() or not paths.db_path.exists() or not paths.policy_path.exists():
        initialize_workspace(
            workspace=workspace, policy_template=DEFAULT_POLICY_TEMPLATE, force=False
        )

    request = read_json_from_path_or_stdin(input_path)
    cfg = LumynConfig(
        policy_path=paths.policy_path,
        store_path=paths.db_path,
        memory_path=paths.workspace / "memory",
    )
    record = decide(request, config=cfg)
    write_json_to_path_or_stdout(record, path=out, pretty=pretty)
