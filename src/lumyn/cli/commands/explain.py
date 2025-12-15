from __future__ import annotations

from pathlib import Path

import typer

from lumyn.store.sqlite import SqliteStore

from ..util import die, resolve_workspace_paths
from .init import DEFAULT_POLICY_TEMPLATE, initialize_workspace

app = typer.Typer(help="Explain a stored DecisionRecord in human-readable form.")


@app.callback(invoke_without_command=True)
def main(
    decision_id: str = typer.Argument(..., help="DecisionRecord decision_id to explain."),
    *,
    workspace: Path = typer.Option(Path(".lumyn"), "--workspace", help="Workspace directory."),
    markdown: bool = typer.Option(False, "--markdown", help="Emit a paste-ready markdown summary."),
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

    verdict = record.get("verdict")
    raw_reason_codes = record.get("reason_codes")
    reason_codes: list[object]
    if isinstance(raw_reason_codes, list):
        reason_codes = raw_reason_codes
    else:
        reason_codes = []

    raw_matched_rules = record.get("matched_rules")
    matched_rules: list[object]
    if isinstance(raw_matched_rules, list):
        matched_rules = raw_matched_rules
    else:
        matched_rules = []

    raw_policy = record.get("policy")
    policy: dict[str, object]
    if isinstance(raw_policy, dict):
        policy = raw_policy
    else:
        policy = {}

    raw_determinism = record.get("determinism")
    determinism: dict[str, object]
    if isinstance(raw_determinism, dict):
        determinism = raw_determinism
    else:
        determinism = {}

    raw_request = record.get("request")
    request: dict[str, object]
    if isinstance(raw_request, dict):
        request = raw_request
    else:
        request = {}

    raw_context = request.get("context")
    context: dict[str, object]
    if isinstance(raw_context, dict):
        context = raw_context
    else:
        context = {}

    if markdown:
        typer.echo(f"# Lumyn decision `{record.get('decision_id')}`")
        typer.echo(f"- created_at: `{record.get('created_at')}`")
        typer.echo(f"- verdict: `{verdict}`")
        typer.echo(f"- reason_codes: `{', '.join([str(x) for x in reason_codes]) or '(none)'}`")
        typer.echo(f"- policy_hash: `{policy.get('policy_hash')}`")
        typer.echo(f"- context_digest: `{context.get('digest')}`")
        typer.echo(f"- inputs_digest: `{determinism.get('inputs_digest')}`")
        if matched_rules:
            typer.echo("")
            typer.echo("## Matched rules")
            for r in matched_rules:
                if not isinstance(r, dict):
                    continue
                typer.echo(
                    f"- `{r.get('stage')}:{r.get('rule_id')}` "
                    f"effect=`{r.get('effect')}` "
                    f"reasons=`{r.get('reason_codes')}`"
                )
        return

    typer.echo(f"decision_id: {record.get('decision_id')}")
    typer.echo(f"created_at: {record.get('created_at')}")
    typer.echo(f"verdict: {verdict}")
    typer.echo(f"reason_codes: {', '.join([str(x) for x in reason_codes]) or '(none)'}")
    if matched_rules:
        typer.echo("matched_rules:")
        for r in matched_rules:
            if not isinstance(r, dict):
                continue
            typer.echo(
                f"  - {r.get('stage')}:{r.get('rule_id')} effect={r.get('effect')} "
                f"reasons={r.get('reason_codes')}"
            )
