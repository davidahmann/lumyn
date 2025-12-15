from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app


def test_failure_similarity_escalates_after_label(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    req1 = {
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
    req2 = dict(req1)
    req2["context"] = {"mode": "digest_only", "digest": "sha256:" + ("b" * 64)}

    request1_path = tmp_path / "request1.json"
    request1_path.write_text(json.dumps(req1), encoding="utf-8")
    request2_path = tmp_path / "request2.json"
    request2_path.write_text(json.dumps(req2), encoding="utf-8")

    request2_path.write_text(json.dumps(req2), encoding="utf-8")

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

    first = runner.invoke(
        app,
        ["decide", "--workspace", str(workspace), "--in", str(request1_path)],
    )  # Explicitly init v0 policy for legacy test
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

    first = runner.invoke(
        app,
        ["decide", "--workspace", str(workspace), str(request1_path)],
    )
    assert first.exit_code == 0
    first_record = json.loads(first.stdout)
    decision_id = first_record["decision_id"]
    assert first_record["verdict"] == "TRUST"

    labeled = runner.invoke(
        app,
        [
            "label",
            decision_id,
            "--workspace",
            str(workspace),
            "--label",
            "failure",
            "--summary",
            "Bad outcome",
        ],
    )
    assert labeled.exit_code == 0

    second = runner.invoke(
        app,
        ["decide", "--workspace", str(workspace), str(request2_path)],
    )
    assert second.exit_code == 0
    second_record = json.loads(second.stdout)
    assert second_record["verdict"] == "ESCALATE"
    assert "FAILURE_MEMORY_SIMILAR_ESCALATE" in second_record["reason_codes"]

    evidence = second_record.get("request", {}).get("evidence", {})
    assert isinstance(evidence, dict)
    assert isinstance(evidence.get("failure_similarity_score"), int | float)
    assert float(evidence["failure_similarity_score"]) >= 0.35
