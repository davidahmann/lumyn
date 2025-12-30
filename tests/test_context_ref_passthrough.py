from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from lumyn.core.decide import LumynConfig, decide_v1
from lumyn.engine.normalize_v1 import compute_inputs_digest_v1, normalize_request_v1
from lumyn.schemas.loaders import load_json_schema


def test_v1_context_ref_is_persisted_and_in_inputs_digest(tmp_path: Path) -> None:
    req = {
        "schema_version": "decision_request.v1",
        "request_id": "req_ctx_ref_001",
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
        "context_ref": {
            "context_id": "ctx_01JZ1S7Y1NQ2A0D5JQK2Q2P3X4",
            "record_hash": "sha256:" + ("b" * 64),
        },
        "interaction_ref": {
            "schema_version": "interaction_ref.v0",
            "mode": "voice",
            "call_id": "call_001",
            "turn_id": "turn_0003",
            "turn_index": 3,
            "jurisdiction": "US-CA",
            "consent_state": "granted",
            "redaction_mode": "default",
            "timeline": [{"index": 0, "at": "2025-12-28T15:00:00Z", "type": "call.started"}],
        },
    }

    Draft202012Validator(load_json_schema("schemas/decision_request.v1.schema.json")).validate(req)

    config = LumynConfig(
        policy_path="policies/starter.v1.yml",
        store_path=tmp_path / "ctx_ref.db",
        memory_enabled=False,
    )
    record = decide_v1(req, config=config)

    Draft202012Validator(load_json_schema("schemas/decision_record.v1.schema.json")).validate(
        record
    )

    assert record.get("context_ref") == req["context_ref"]
    assert record["request"].get("context_ref") == req["context_ref"]
    assert record.get("interaction_ref") == req["interaction_ref"]
    assert record["request"].get("interaction_ref") == req["interaction_ref"]

    normalized = normalize_request_v1(record["request"])
    expected_digest = compute_inputs_digest_v1(record["request"], normalized=normalized)
    assert record["determinism"]["inputs_digest"] == expected_digest
