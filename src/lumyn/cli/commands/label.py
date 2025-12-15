from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from lumyn.engine.normalize import normalize_request
from lumyn.store.sqlite import SqliteStore

from ..util import die, resolve_workspace_paths
from .init import DEFAULT_POLICY_TEMPLATE, initialize_workspace

app = typer.Typer(help="Append a label/event to a decision and update memory.")


def _amount_bucket(amount_usd: float | None) -> str | None:
    if amount_usd is None:
        return None
    if amount_usd < 50:
        return "small"
    if amount_usd < 200:
        return "medium"
    return "large"


def _extract_feature_and_action_type(
    record: dict[str, Any],
) -> tuple[str, dict[str, Any], str | None]:
    request = record.get("request")
    if not isinstance(request, dict):
        die("decision record missing request object")

    request_dict: dict[str, Any] = request
    normalized = normalize_request(request_dict)

    raw_action = request_dict.get("action")
    action: dict[str, Any]
    if isinstance(raw_action, dict):
        action = raw_action
    else:
        action = {}
    feature: dict[str, Any] = {
        "action_type": normalized.action_type,
        "amount_currency": normalized.amount_currency,
        "amount_usd_bucket": _amount_bucket(normalized.amount_usd),
        "tags": action.get("tags", []) if isinstance(action.get("tags"), list) else [],
    }

    raw_subject = request_dict.get("subject")
    subject: dict[str, Any]
    if isinstance(raw_subject, dict):
        subject = raw_subject
    else:
        subject = {}
    tenant_id = subject.get("tenant_id") if isinstance(subject.get("tenant_id"), str) else None
    return normalized.action_type, feature, tenant_id


@app.callback(invoke_without_command=True)
def main(
    decision_id: str = typer.Argument(..., help="DecisionRecord decision_id to label."),
    *,
    label: str = typer.Option(
        ...,
        "--label",
        help="Label to apply (use 'failure' to influence similarity heuristics).",
    ),
    summary: str = typer.Option("", "--summary", help="Short label summary (optional)."),
    workspace: Path = typer.Option(Path(".lumyn"), "--workspace", help="Workspace directory."),
) -> None:
    label_norm = label.strip().lower()
    if label_norm == "":
        die("label cannot be empty")

    paths = resolve_workspace_paths(workspace)
    if not paths.workspace.exists() or not paths.db_path.exists() or not paths.policy_path.exists():
        initialize_workspace(
            workspace=workspace, policy_template=DEFAULT_POLICY_TEMPLATE, force=False
        )

    store = SqliteStore(paths.db_path)
    record = store.get_decision_record(decision_id)
    if record is None:
        die(f"decision not found: {decision_id}")

    action_type, feature, tenant_id = _extract_feature_and_action_type(record)

    if summary.strip() == "":
        request = record.get("request")
        if isinstance(request, dict) and isinstance(request.get("action"), dict):
            action: dict[str, Any] = request["action"]
        else:
            action = {}
        intent = action.get("intent") if isinstance(action.get("intent"), str) else None
        verdict = record.get("verdict")
        summary = f"{action_type}: {intent or '(no intent)'} -> {verdict} ({label_norm})"

    event_id = store.append_decision_event(
        decision_id,
        "label",
        {"label": label_norm, "summary": summary, "source": "cli"},
    )
    memory = store.add_memory_item(
        tenant_id=tenant_id,
        label=label_norm,
        action_type=action_type,
        feature=feature,
        summary=summary,
        source_decision_id=decision_id,
    )

    typer.echo(f"event_id: {event_id}")
    typer.echo(f"memory_id: {memory.memory_id}")
