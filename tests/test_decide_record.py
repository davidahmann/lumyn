from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from lumyn import LumynConfig, decide


def test_decide_emits_schema_valid_record(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    cfg = LumynConfig(policy_path="policies/lumyn-support.v0.yml", store_path=store_path)

    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "agent", "id": "agent-1", "tenant_id": "acme"},
        "action": {
            "type": "support.refund",
            "intent": "Refund duplicate charge for order 82731",
            "amount": {"value": 201.0, "currency": "USD"},
        },
        "evidence": {"ticket_id": "ZD-1", "order_id": "82731", "customer_id": "C-9"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        },
    }

    record = decide(request, config=cfg)
    assert record["schema_version"] == "decision_record.v0"
    assert record["verdict"] in {"TRUST", "ABSTAIN", "ESCALATE", "QUERY"}

    schema = Draft202012Validator(
        __import__("json").loads(Path("schemas/decision_record.v0.schema.json").read_text("utf-8"))
    )
    schema.validate(record)


def test_decide_persists_before_return(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    cfg = LumynConfig(policy_path="policies/lumyn-support.v0.yml", store_path=store_path)

    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "agent", "id": "agent-2", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "evidence": {"ticket_id": "ZD-4002"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }

    record = decide(request, config=cfg)

    from lumyn.store.sqlite import SqliteStore

    store = SqliteStore(store_path)
    got = store.get_decision_record(record["decision_id"])
    assert got is not None
    assert got["decision_id"] == record["decision_id"]
