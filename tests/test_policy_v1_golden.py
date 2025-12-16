import os
from collections.abc import Generator
from typing import Any, cast

import pytest
import yaml

from lumyn.core.decide import LumynConfig, decide_v1


@pytest.fixture
def starter_policy_v1() -> dict[str, Any]:
    with open("policies/starter.v1.yml") as f:
        return cast(dict[str, Any], yaml.safe_load(f))


@pytest.fixture
def clean_store_golden() -> Generator[str, None, None]:
    store_path = ".lumyn/test_golden.db"
    if os.path.exists(store_path):
        os.remove(store_path)
    yield store_path
    if os.path.exists(store_path):
        os.remove(store_path)


def test_requirements_missing_evidence(
    starter_policy_v1: dict[str, Any], clean_store_golden: str
) -> None:
    # R001: Missing ticket_id -> DENY
    request = {
        "schema_version": "decision_request.v1",
        "request_id": "req_missing_evidence",
        "tenant": {"tenant_id": "t1"},
        "subject": {"type": "user", "id": "u1"},
        "action": {
            "type": "support.refund",
            "intent": "refund ticket",
            "amount": {"value": 10.0, "currency": "USD"},
        },
        "context": {
            "mode": "digest_only",
            "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        },
        "evidence": {},  # Empty evidence
    }

    config = LumynConfig(store_path=clean_store_golden, policy_path="policies/starter.v1.yml")
    record = decide_v1(request, config=config)

    assert record["verdict"] == "DENY"
    assert "MISSING_EVIDENCE_REFUND" in record["reason_codes"]
    assert any(q["field"] == "evidence.ticket_id" for q in record["queries"])


def test_hard_block_sanctions(starter_policy_v1: dict[str, Any], clean_store_golden: str) -> None:
    # R020: High risk payment -> ABSTAIN
    request = {
        "schema_version": "decision_request.v1",
        "request_id": "req_sanctions",
        "tenant": {"tenant_id": "t1"},
        "subject": {"type": "user", "id": "u1"},
        "action": {
            "type": "support.refund",
            "intent": "risky refund",
            "amount": {"value": 10.0, "currency": "USD"},
        },
        "context": {
            "mode": "digest_only",
            "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        },
        "evidence": {
            "ticket_id": "t1",
            "order_id": "o1",
            "customer_id": "c1",
            "payment_instrument_risk": "high",
        },
    }

    config = LumynConfig(store_path=clean_store_golden, policy_path="policies/starter.v1.yml")
    record = decide_v1(request, config=config)

    assert record["verdict"] == "ABSTAIN"
    assert "PAYMENT_INSTRUMENT_HIGH_RISK" in record["reason_codes"]


def test_escalation_large_amount(
    starter_policy_v1: dict[str, Any], clean_store_golden: str
) -> None:
    # R030: Amount > 200 -> ESCALATE
    request = {
        "schema_version": "decision_request.v1",
        "request_id": "req_large",
        "tenant": {"tenant_id": "t1"},
        "subject": {"type": "user", "id": "u1"},
        "action": {
            "type": "support.refund",
            "intent": "large refund",
            "amount": {"value": 201.0, "currency": "USD"},
        },
        "context": {
            "mode": "digest_only",
            "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        },
        "evidence": {
            "ticket_id": "t1",
            "order_id": "o1",
            "customer_id": "c1",
            "payment_instrument_risk": "low",
        },
    }
    config = LumynConfig(store_path=clean_store_golden, policy_path="policies/starter.v1.yml")
    record = decide_v1(request, config=config)

    assert record["verdict"] == "ESCALATE"
    assert "REFUND_OVER_ESCALATION_LIMIT" in record["reason_codes"]


def test_trust_path_allow(starter_policy_v1: dict[str, Any], clean_store_golden: str) -> None:
    # R050: Low risk, small amount -> ALLOW
    request = {
        "schema_version": "decision_request.v1",
        "request_id": "req_allow",
        "tenant": {"tenant_id": "t1"},
        "subject": {"type": "user", "id": "u1"},
        "action": {
            "type": "support.refund",
            "intent": "trusted refund",
            "amount": {"value": 20.0, "currency": "USD"},
        },
        "context": {
            "mode": "digest_only",
            "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        },
        "evidence": {
            "ticket_id": "t1",
            "order_id": "o1",
            "customer_id": "c1",
            "payment_instrument_risk": "low",
            "chargeback_risk": 0.1,
            "previous_refund_count_90d": 0,
            "customer_age_days": 100,
        },
    }
    config = LumynConfig(store_path=clean_store_golden, policy_path="policies/starter.v1.yml")
    record = decide_v1(request, config=config)

    assert record["verdict"] == "ALLOW"
    assert "REFUND_SMALL_LOW_RISK" in record["reason_codes"]
    assert any(o["title"] == "Verify ticket exists" for o in record["obligations"])
