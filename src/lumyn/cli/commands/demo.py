from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import typer

from lumyn.core.decide import LumynConfig, decide

from ..util import resolve_workspace_paths, write_json_to_path_or_stdout
from .init import DEFAULT_POLICY_TEMPLATE, initialize_workspace
from .label import main as label_main

app = typer.Typer(help="Run a local demo (creates multiple Decision Records).")


def _demo_requests() -> list[dict[str, Any]]:
    return [
        {
            "schema_version": "decision_request.v1",
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
            "schema_version": "decision_request.v1",
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
            "schema_version": "decision_request.v1",
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
    story: bool = typer.Option(
        False,
        "--story",
        help="Print a narrative demo that labels a failure and re-runs a similar decision.",
    ),
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

    cfg = LumynConfig(
        policy_path=paths.policy_path,
        store_path=paths.db_path,
        memory_path=paths.workspace / "memory",
    )
    if story:
        req1 = copy.deepcopy(_demo_requests()[0])
        action_obj = req1.get("action")
        if isinstance(action_obj, dict):
            amount_obj = action_obj.get("amount")
            if isinstance(amount_obj, dict):
                amount_obj["value"] = 12.0

        evidence_obj = req1.get("evidence")
        evidence: dict[str, Any]
        if isinstance(evidence_obj, dict):
            evidence = evidence_obj
        else:
            evidence = {}
            req1["evidence"] = evidence
        evidence.setdefault("customer_age_days", 180)
        evidence.setdefault("previous_refund_count_90d", 0)
        evidence.setdefault("chargeback_risk", 0.05)
        evidence.setdefault("payment_instrument_risk", "low")

        req2 = copy.deepcopy(req1)
        req2["context"] = {
            "mode": "digest_only",
            "digest": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
        }

        typer.echo("Lumyn demo story")
        typer.echo("1) Decide on a refund request")
        r1 = decide(req1, config=cfg)
        typer.echo(f"   decision_id: {r1['decision_id']}")
        typer.echo(f"   verdict: {r1['verdict']}")
        typer.echo(f"   reason_codes: {', '.join(r1.get('reason_codes', []))}")

        typer.echo("2) Label the outcome as a failure (updates Experience Memory)")
        label_main(
            r1["decision_id"],
            label="failure",
            summary="Demo: refund led to bad outcome",
            workspace=workspace,
        )

        typer.echo("3) Re-run a similar decision (should reflect memory in policy + risk_signals)")
        r2 = decide(req2, config=cfg)
        similarity = 0.0
        risk_signals = r2.get("risk_signals")
        if isinstance(risk_signals, dict):
            failure_similarity = risk_signals.get("failure_similarity")
            if isinstance(failure_similarity, dict):
                score = failure_similarity.get("score")
                if isinstance(score, int | float):
                    similarity = float(score)
        typer.echo(f"   decision_id: {r2['decision_id']}")
        typer.echo(f"   verdict: {r2['verdict']}")
        typer.echo(f"   reason_codes: {', '.join(r2.get('reason_codes', []))}")
        typer.echo(f"   failure_similarity.score: {similarity}")
        return

    records = [decide(req, config=cfg) for req in _demo_requests()]

    write_json_to_path_or_stdout(records, path=out, pretty=pretty)
