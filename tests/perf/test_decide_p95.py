from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from lumyn.core.decide import LumynConfig, decide


def _p95_ms(samples_ms: list[float]) -> float:
    samples_ms = sorted(samples_ms)
    if not samples_ms:
        return 0.0
    idx = int(0.95 * (len(samples_ms) - 1))
    return samples_ms[idx]


def test_decide_p95_smoke(tmp_path: Path) -> None:
    if os.getenv("LUMYN_SKIP_PERF") == "1":
        pytest.skip("set LUMYN_SKIP_PERF=1 to skip perf smoke")

    p95_budget_ms = float(os.getenv("LUMYN_P95_MS", "50"))

    cfg = LumynConfig(
        policy_path="policies/lumyn-support.v0.yml",
        store_path=tmp_path / "perf.db",
    )
    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "agent", "id": "agent-1", "tenant_id": "acme"},
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
        "context": {"mode": "digest_only", "digest": "sha256:" + ("d" * 64)},
    }

    for _ in range(25):
        decide(request, config=cfg)

    samples_ms: list[float] = []
    for _ in range(200):
        t0 = time.perf_counter()
        decide(request, config=cfg)
        samples_ms.append((time.perf_counter() - t0) * 1000.0)

    assert _p95_ms(samples_ms) <= p95_budget_ms
