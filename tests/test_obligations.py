from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app


def test_decision_record_includes_obligations_when_policy_sets_them(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": "decision_request.v0",
                "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
                "action": {
                    "type": "support.refund",
                    "intent": "Refund duplicate charge for order 82731",
                    "amount": {"value": 12.0, "currency": "USD"},
                    "tags": ["duplicate_charge"],
                },
                "evidence": {
                    "ticket_id": "ZD-1001",
                    "order_id": "82731",
                    "customer_id": "C-9",
                    "customer_age_days": 180,
                    "previous_refund_count_90d": 0,
                    "chargeback_risk": 0.05,
                    "payment_instrument_risk": "low",
                },
                "context": {"mode": "digest_only", "digest": "sha256:" + ("a" * 64)},
            }
        ),
        encoding="utf-8",
    )

    # Explicitly init v0 policy for legacy test
    runner.invoke(
        app,
        [
            "init",
            "--workspace",
            str(workspace),
            "--policy-template",
            "policies/lumyn-support.v0.yml",
        ],
    )

    decided = runner.invoke(app, ["decide", "--workspace", str(workspace), str(request_path)])
    assert decided.exit_code == 0
    record = json.loads(decided.stdout)
    obligations = record.get("obligations", [])
    assert isinstance(obligations, list)
    assert obligations, "expected obligations from starter policy trust rule"


def test_cli_explain_markdown_includes_obligations(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": "decision_request.v0",
                "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
                "action": {
                    "type": "support.refund",
                    "intent": "Refund duplicate charge for order 82731",
                    "amount": {"value": 12.0, "currency": "USD"},
                    "tags": ["duplicate_charge"],
                },
                "evidence": {
                    "ticket_id": "ZD-1001",
                    "order_id": "82731",
                    "customer_id": "C-9",
                    "customer_age_days": 180,
                    "previous_refund_count_90d": 0,
                    "chargeback_risk": 0.05,
                    "payment_instrument_risk": "low",
                },
                "context": {"mode": "digest_only", "digest": "sha256:" + ("a" * 64)},
            }
        ),
        encoding="utf-8",
    )

    # Explicitly init v0 policy for legacy test
    runner.invoke(
        app,
        [
            "init",
            "--workspace",
            str(workspace),
            "--policy-template",
            "policies/lumyn-support.v0.yml",
        ],
    )

    decided = runner.invoke(app, ["decide", "--workspace", str(workspace), str(request_path)])
    assert decided.exit_code == 0
    record = json.loads(decided.stdout)
    decision_id = record["decision_id"]

    explained = runner.invoke(
        app,
        ["explain", decision_id, "--workspace", str(workspace), "--markdown"],
    )
    assert explained.exit_code == 0
    assert "## Obligations" in explained.stdout
