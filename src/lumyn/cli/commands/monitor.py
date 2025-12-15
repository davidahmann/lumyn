from __future__ import annotations

import time
from pathlib import Path

import typer

from lumyn.cli.util import resolve_workspace_paths
from lumyn.store.sqlite import SqliteStore


def main(
    workspace: Path = typer.Option(
        Path(".lumyn"), "--workspace", "-w", help="Workspace directory."
    ),
    interval: float = typer.Option(1.0, "--interval", "-i", help="Poll interval in seconds."),
    limit: int = typer.Option(
        50, "--limit", "-n", help="Number of recent records to show initially."
    ),
) -> None:
    """
    Live monitor of decision traffic (Matrix style).
    """
    paths = resolve_workspace_paths(workspace)
    if not paths.db_path.exists():
        typer.secho(f"Database not found at {paths.db_path}", fg=typer.colors.RED)
        raise typer.Exit(1)

    store = SqliteStore(paths.db_path)
    # We rely on raw SQL access here for efficient polling of new rows
    # The store API doesn't expose "get after ID" easily, so we extend it privately here or
    # valid use of public connection

    typer.secho("Connecting to the Matrix...", fg=typer.colors.GREEN, bold=True)
    time.sleep(0.5)

    last_rowid = 0

    # Initial catchup (if limit > 0)
    with store.connect() as conn:
        # Get max rowid first
        cur = conn.execute("SELECT MAX(rowid) FROM decisions")
        max_id = cur.fetchone()[0]
        if max_id:
            last_rowid = max_id - limit  # Start 'limit' records back
            if last_rowid < 0:
                last_rowid = 0
        else:
            last_rowid = 0

    try:
        while True:
            # Poll loop
            new_rows = []
            with store.connect() as conn:
                cur = conn.execute(
                    "SELECT rowid, verdict, action_type, subject_id, created_at FROM decisions "
                    "WHERE rowid > ? ORDER BY rowid ASC",
                    (last_rowid,),
                )
                new_rows = cur.fetchall()

            for row in new_rows:
                last_rowid = row["rowid"]
                verdict = row["verdict"]
                action = row["action_type"]
                subject = row["subject_id"] or "?"
                ts = row["created_at"]

                # Colorize
                color = typer.colors.WHITE
                if verdict == "ALLOW":
                    color = typer.colors.GREEN
                elif verdict == "DENY":
                    color = typer.colors.RED
                elif verdict == "ESCALATE":
                    color = typer.colors.YELLOW
                elif verdict == "ABSTAIN":
                    color = typer.colors.MAGENTA

                # Output format: [TIMESTAMP] VERDICT Action Subject
                # Truncate timestamp to HH:MM:SS
                time_str = ts.split("T")[-1].split(".")[0]

                typer.secho(f"[{time_str}] ", fg=typer.colors.CYAN, nl=False)
                typer.secho(f"{verdict:<8} ", fg=color, bold=True, nl=False)
                typer.secho(f"{action:<25} ", fg=typer.colors.WHITE, nl=False)
                typer.secho(f"{subject}", fg=typer.colors.BRIGHT_BLACK)

            time.sleep(interval)

    except KeyboardInterrupt:
        typer.echo("")
        typer.secho("Disconnected.", fg=typer.colors.GREEN)
        raise typer.Exit(0)
