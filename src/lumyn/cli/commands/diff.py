from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, cast

import typer

from lumyn.core.decide import LumynConfig, decide
from lumyn.policy.loader import load_policy
from lumyn.store.sqlite import SqliteStore

# app = typer.Typer(help="Run regression tests by comparing a policy against past decisions.")


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        typer.secho(f"Error: Dataset not found: {path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return cast(list[dict[str, Any]], data)
        # Handle single record wrapping? Or error?
        if isinstance(data, dict) and "records" in data:
            return cast(list[dict[str, Any]], data["records"])
        return [cast(dict[str, Any], data)]  # Single obj
    except json.JSONDecodeError:
        typer.secho(f"Error: Invalid JSON in {path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)


def _print_table(rows: list[list[str]], headers: list[str]) -> None:
    # Simple text table
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    # Header
    header_str = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    typer.echo(header_str)
    typer.echo("-" * len(header_str))

    # Rows
    for row in rows:
        row_str = "  ".join(val.ljust(col_widths[i]) for i, val in enumerate(row))
        # Colorize row based on change?
        # We can't easily mixed color strings with len() calc without stripping ansi.
        # Let's just print plain for now or minimal color.
        typer.echo(row_str)


def main(
    dataset: Path = typer.Argument(..., help="JSON file containing historical Decision Records."),
    policy: Path = typer.Option(..., "--policy", "-p", help="Path to the candidate policy file."),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show details for all records, not just changes."
    ),
) -> None:
    """
    Run the candidate POLICY against the DATASET of past records and report changes.
    """

    # 1. Load Policy
    if not policy.exists():
        typer.secho(f"Error: Policy not found: {policy}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    # We load config with strict enforcement
    config = LumynConfig(policy_path=str(policy), memory_enabled=False)
    # Pre-validate policy load to fail fast
    try:
        loaded_policy = load_policy(policy)
    except Exception as e:
        typer.secho(f"Error loading policy: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    # 2. Setup ephemeral store (to ignore existing DB and simulate fresh replay with accumulation)
    # We use a temporary directory because SqliteStore creates WAL/SHM files.
    # ":memory:" in SqliteStore logic treats it as a file named ":memory:", so we prefer temp dir.
    with tempfile.TemporaryDirectory() as tmp_dir:
        store_path = Path(tmp_dir) / "replay_session.db"
        store = SqliteStore(store_path)

        # 3. Load Dataset
        records = _load_records(dataset)
        if not records:
            typer.secho("Dataset is empty.", fg=typer.colors.YELLOW)
            return

        typer.secho(
            f"Loaded {len(records)} records. Replaying against {policy.name}...",
            fg=typer.colors.BLUE,
        )

        # 3. Replay
        changes = []
        same = 0
        errors = 0

        for original_rec in records:
            original_req = original_rec.get("request")
            if not original_req:
                errors += 1
                continue

            try:
                # Pass ephemeral store
                new_rec = decide(
                    original_req, config=config, store=store, loaded_policy=loaded_policy
                )
            except Exception:
                errors += 1
                continue

            original_verdict = original_rec.get("verdict")
            new_verdict = new_rec.get("verdict")

            # Check match
            if original_verdict == new_verdict:
                same += 1
            else:
                changes.append(
                    {
                        "id": original_rec.get("decision_id", "?"),
                        "old": original_verdict,
                        "new": new_verdict,
                        "old_reasons": ",".join(original_rec.get("reason_codes", [])),
                        "new_reasons": ",".join(new_rec.get("reason_codes", [])),
                    }
                )

        # 4. Report
        typer.echo("")
        typer.secho("--- Diff Report ---", bold=True)
        typer.echo(f"Total:   {len(records)}")
        typer.secho(f"Same:    {same}", fg=typer.colors.GREEN)

        if errors:
            typer.secho(f"Errors:  {errors} (skipped)", fg=typer.colors.YELLOW)

        if not changes:
            typer.secho(
                "No regressions found. verdicts match 100%.", fg=typer.colors.GREEN, bold=True
            )
            return

        typer.secho(f"Changes: {len(changes)}", fg=typer.colors.RED, bold=True)
        typer.echo("")

        # Table output
        headers = ["Decision ID", "Old", "New", "Reason Diff"]
        rows = []

        for c in changes:
            rows.append(
                [
                    str(c["id"]),
                    str(c["old"]),
                    str(c["new"]),
                    f"{c['old_reasons']} -> {c['new_reasons']}",
                ]
            )

        _print_table(rows, headers)

        raise typer.Exit(code=1)
