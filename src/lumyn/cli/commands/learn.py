import json
import sqlite3
from typing import Annotated

import typer
from rich.console import Console

from lumyn.engine.normalize_v1 import normalize_request_v1
from lumyn.memory.client import MemoryStore
from lumyn.memory.embed import ProjectionLayer
from lumyn.memory.types import Experience

console = Console()


def main(
    decision_id: Annotated[str, typer.Argument(help="The ULID of the decision")],
    outcome: Annotated[str, typer.Option(help="SUCCESS or FAILURE")] = "SUCCESS",
    severity: Annotated[int, typer.Option(help="Severity 1-5")] = 1,
    db: Annotated[str, typer.Option(help="Path to SQLite DB")] = ".lumyn/lumyn.db",
    memory_path: Annotated[str, typer.Option(help="Path to Memory DB")] = ".lumyn/memory",
) -> None:
    """
    Ingest a past decision into memory with a verified outcome.
    """
    outcome = outcome.upper()
    if outcome not in ("SUCCESS", "FAILURE"):
        console.print("[red]Outcome must be SUCCESS or FAILURE[/red]")
        raise typer.Exit(1)

    outcome_val = 1 if outcome == "SUCCESS" else -1

    # 1. Fetch Record
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT record_json FROM decisions WHERE decision_id = ?", (decision_id,))
    row = cursor.fetchone()
    if not row:
        console.print(f"[red]Decision {decision_id} not found in {db}[/red]")
        raise typer.Exit(1)

    record = json.loads(row["record_json"])
    original_verdict = record.get("verdict", "UNKNOWN")
    raw_request = record.get("request", {})
    timestamp = record.get("created_at", "")

    # 2. Project
    norm = normalize_request_v1(raw_request)
    proj = ProjectionLayer()
    vector = proj.embed_request(norm)

    # 3. Store
    exp = Experience(
        decision_id=decision_id,
        vector=vector,
        outcome=outcome_val,
        severity=severity,
        original_verdict=original_verdict,
        timestamp=timestamp,
    )

    mem = MemoryStore(db_path=memory_path)
    mem.add_experiences([exp])

    console.print(f"[green]Learned from {decision_id}[/green]")
    console.print(f"Outcome: {outcome} ({outcome_val})")
    console.print("Memory updated.")
