from __future__ import annotations

from pathlib import Path

import typer
import yaml

from lumyn.tools.migrate_v1 import migrate_policy_v0_to_v1

from ..util import die

app = typer.Typer(help="Migrate a policy from v0 to v1.")


@app.callback(invoke_without_command=True)
def main(
    policy_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Path to the v0 policy file to migrate.",
    ),
    out: Path = typer.Option(
        None, "--out", "-o", help="Path to write the v1 policy. Defaults to <policy>.v1.yml."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite output file if it exists."),
) -> None:
    """
    Migrate a policy from v0 to v1 format.
    """
    if not out:
        out = policy_path.with_suffix(".v1.yml")

    if out.exists() and not force:
        die(f"Output file {out} already exists. Use --force to overwrite.")

    try:
        policy_v0 = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Failed to parse policy file: {e}")

    policy_v1, warnings = migrate_policy_v0_to_v1(policy_v0)

    # Write output
    try:
        with open(out, "w") as f:
            yaml.dump(policy_v1, f, sort_keys=False)
    except Exception as e:
        die(f"Failed to write output file: {e}")

    typer.echo(f"Successfully migrated policy to {out}")
    if warnings:
        typer.echo("\nWarnings during migration:")
        for w in warnings:
            typer.echo(f"- {w}", err=True)
