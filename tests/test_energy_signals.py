from __future__ import annotations

from pathlib import Path

import pytest

from lumyn.core.decide import LumynConfig, decide_v1
from lumyn.engine.energy import compute_energy_v1


def test_v1_record_includes_energy_and_is_deterministic(tmp_path: Path) -> None:
    cfg1 = LumynConfig(
        policy_path="policies/starter.v1.yml",
        store_path=tmp_path / "e1.db",
        memory_enabled=False,
    )
    cfg2 = LumynConfig(
        policy_path="policies/starter.v1.yml",
        store_path=tmp_path / "e2.db",
        memory_enabled=False,
    )

    req = {
        "schema_version": "decision_request.v1",
        "request_id": "req_energy_001",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {
            "type": "support.refund",
            "intent": "Refund duplicate charge",
            "amount": {"value": 20.0, "currency": "USD"},
        },
        "evidence": {
            "ticket_id": "ZD-1001",
            "order_id": "82731",
            "customer_id": "C-9",
            "payment_instrument_risk": "low",
            "chargeback_risk": 0.05,
            "previous_refund_count_90d": 0,
            "customer_age_days": 180,
        },
        "context": {"mode": "digest_only", "digest": "sha256:" + ("a" * 64)},
    }

    r1 = decide_v1(req, config=cfg1)
    r2 = decide_v1(req, config=cfg2)

    e1 = r1["risk_signals"]["energy"]
    e2 = r2["risk_signals"]["energy"]

    assert e1["schema_version"] == "energy.v1"
    assert e2["schema_version"] == "energy.v1"
    assert e1["total"] == pytest.approx(e2["total"])

    expected = compute_energy_v1(
        verdict=r1["verdict"],
        uncertainty_score=r1["risk_signals"]["uncertainty_score"],
        failure_similarity_score=r1["risk_signals"]["failure_similarity"]["score"],
        success_similarity_score=r1["risk_signals"]["success_similarity"]["score"],
    )
    assert e1["total"] == pytest.approx(expected.total)
