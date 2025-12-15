from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from lumyn.core.decide import LumynConfig, decide

from ..util import resolve_workspace_paths, write_json_to_path_or_stdout
from .init import DEFAULT_POLICY_TEMPLATE, initialize_workspace

app = typer.Typer(help="Run a local demo (creates multiple Decision Records).")


def _demo_requests() -> list[dict[str, Any]]:
    return [
        {
            "schema_version": "decision_request.v0",
            "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
            "action": {
                "type": "support.refund",
                "intent": "Refund duplicate charge for order 82731",
                "target": {"system": "stripe", "resource_type": "charge", "resource_id": "ch_123"},
                "amount": {"value": 42.5, "currency": "USD"},
                "tags": ["duplicate_charge"],
            },
            "evidence": {"ticket_id": "ZD-1001", "order_id": "82731", "customer_id": "C-9"},
            "context": {
                "mode": "digest_only",
                "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            },
        },
        {
            "schema_version": "decision_request.v0",
            "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
            "action": {
                "type": "support.refund",
                "intent": "Refund for order 99999 (missing evidence: no ticket_id)",
                "amount": {"value": 250.0, "currency": "USD"},
                "tags": ["high_amount"],
            },
            "evidence": {"order_id": "99999", "customer_id": "C-21"},
            "context": {
                "mode": "digest_only",
                "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            },
        },
        {
            "schema_version": "decision_request.v0",
            "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
            "action": {"type": "support.update_ticket", "intent": "Update ticket ZD-4002"},
            "evidence": {"ticket_id": "ZD-4002"},
            "context": {
                "mode": "digest_only",
                "digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            },
        },
    ]


@app.callback(invoke_without_command=True)
def main(
    *,
    workspace: Path = typer.Option(Path(".lumyn"), "--workspace", help="Workspace directory."),
    out: Path = typer.Option(
        Path("-"),
        "--out",
        help="Write JSON array of DecisionRecords to file (or '-' for stdout).",
    ),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    paths = resolve_workspace_paths(workspace)
    if not paths.workspace.exists():
        initialize_workspace(
            workspace=workspace, policy_template=DEFAULT_POLICY_TEMPLATE, force=False
        )
    elif not paths.db_path.exists() or not paths.policy_path.exists():
        initialize_workspace(
            workspace=workspace, policy_template=DEFAULT_POLICY_TEMPLATE, force=False
        )

    cfg = LumynConfig(policy_path=paths.policy_path, store_path=paths.db_path)
    records = [decide(req, config=cfg) for req in _demo_requests()]

    write_json_to_path_or_stdout(records, path=out, pretty=pretty)
