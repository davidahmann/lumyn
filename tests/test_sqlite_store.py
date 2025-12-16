from __future__ import annotations

from pathlib import Path

from lumyn.store.sqlite import SqliteStore


def test_sqlite_store_init_and_roundtrip_decision(tmp_path: Path) -> None:
    db_path = tmp_path / "lumyn.db"
    store = SqliteStore(db_path)
    store.init()

    record = {
        "schema_version": "decision_record.v0",
        "decision_id": "dec_01JZ1S7Y1NQ2A0D5JQK2Q2P3X4",
        "created_at": "2026-01-13T14:12:05Z",
        "request": {
            "schema_version": "decision_request.v0",
            "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
            "action": {
                "type": "support.refund",
                "intent": "Refund duplicate charge for order 82731",
                "target": {"system": "stripe", "resource_type": "charge", "resource_id": "ch_123"},
                "amount": {"value": 201.0, "currency": "USD"},
            },
            "evidence": {"ticket_id": "ZD-1001", "order_id": "82731", "customer_id": "C-9"},
            "context": {
                "mode": "digest_only",
                "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            },
        },
        "policy": {
            "policy_id": "lumyn-support",
            "policy_version": "0.1.0",
            "policy_hash": (
                "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            ),
            "mode": "enforce",
        },
        "verdict": "ESCALATE",
        "reason_codes": ["REFUND_OVER_ESCALATION_LIMIT"],
        "matched_rules": [],
        "risk_signals": {
            "uncertainty_score": 0.12,
            "failure_similarity": {"score": 0.07, "top_k": []},
        },
        "determinism": {
            "engine_version": "0.1.0",
            "evaluation_order": [
                "REQUIREMENTS",
                "HARD_BLOCKS",
                "ESCALATIONS",
                "TRUST_PATHS",
                "DEFAULT",
            ],
            "inputs_digest": (
                "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
            ),
        },
    }

    store.put_decision_record(record)

    store2 = SqliteStore(db_path)
    got = store2.get_decision_record(str(record["decision_id"]))
    assert got == record


def test_sqlite_store_memory_items_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "lumyn.db"
    store = SqliteStore(db_path)
    store.init()

    item = store.add_memory_item(
        tenant_id="acme",
        label="failure",
        action_type="support.refund",
        feature={"action_type": "support.refund", "amount_bucket": "small"},
        summary="Auto-refunded wrong order.",
        source_decision_id=None,
        memory_id="mem_0001",
        created_at="2026-01-13T14:12:05Z",
    )
    assert item.memory_id == "mem_0001"

    items = store.list_memory_items(tenant_id="acme", action_type="support.refund", label="failure")
    assert len(items) == 1
    assert items[0].memory_id == "mem_0001"
    assert items[0].feature["amount_bucket"] == "small"
