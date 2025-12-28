import importlib
import os

import pytest

from lumyn.core.decide import LumynConfig, decide_v1
from lumyn.engine.normalize_v1 import compute_memory_snapshot_digest_v1
from lumyn.memory.types import Experience, MemoryHit
from lumyn.store.sqlite import SqliteStore


@pytest.fixture
def clean_store():
    store_path = ".lumyn/test_v1.db"
    if os.path.exists(store_path):
        os.remove(store_path)
    yield store_path
    if os.path.exists(store_path):
        os.remove(store_path)


def test_decide_v1_basic_flow(clean_store) -> None:
    # Setup
    config = LumynConfig(
        store_path=clean_store,
        policy_path="policies/lumyn-support.v0.yml",
        memory_enabled=False,
    )  # Using v0 implementation since v1 not ready yet in Epic V1-2B

    # But wait, decide_v1 uses v1 normalization.
    # If I use v0 policy (which has TRUST/QUERY), evaluate_policy_v1 will map TRUST->ALLOW
    # (as implemented in evaluator_v1 check for strict v1 verdicts if strict precedence is used)
    # My evaluator_v1.py has mapping logic? No, I commented it:
    # "if effect == "TRUST": effect = "ALLOW" ..."
    # I did implement that mapping in the code I wrote.

    request = {
        "schema_version": "decision_request.v1",
        "request_id": "req_v1_test_001",
        "tenant": {"tenant_id": "test", "environment": "dev"},
        "subject": {"type": "service", "id": "test-service"},
        "action": {
            "type": "support.refund",
            "intent": "refund test",
            "amount": {"value": 10.0, "currency": "USD"},
        },
        "context": {
            "mode": "digest_only",
            "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        },
        "evidence": {
            "ticket_id": "123",  # Required by lumyn-support policy
            "previous_refund_count_90d": 0,
        },
    }

    # Execute
    record = decide_v1(request, config=config)

    # Assert
    assert record["schema_version"] == "decision_record.v1"
    assert record["verdict"] in ["ALLOW", "DENY", "ABSTAIN", "ESCALATE"]
    assert "determinism" in record
    assert record["determinism"]["inputs_digest"].startswith("sha256:")

    # Check persistence
    store = SqliteStore(clean_store)
    store.init()
    stored_record = store.get_decision_record(record["decision_id"])
    assert stored_record is not None
    assert stored_record["decision_id"] == record["decision_id"]
    assert stored_record["schema_version"] == "decision_record.v1"


def test_decide_v1_emits_memory_snapshot_digest(clean_store, tmp_path, monkeypatch) -> None:
    decide_mod = importlib.import_module("lumyn.core.decide")

    class StubProjectionLayer:
        def __init__(self) -> None:
            self.model_name = "stub/projection"

        def embed_request(self, normalized) -> list[float]:  # noqa: ANN001
            return [0.0]

    class StubMemoryStore:
        def __init__(self, db_path) -> None:  # noqa: ANN001
            pass

        def search(self, query_vector, limit: int = 5) -> list[MemoryHit]:  # noqa: ANN001
            exp = Experience(
                decision_id="dec_001",
                vector=[0.0],
                outcome=-1,
                severity=1,
                original_verdict="ALLOW",
                timestamp="",
            )
            return [MemoryHit(experience=exp, score=0.95)]

    monkeypatch.setattr(decide_mod, "ProjectionLayer", StubProjectionLayer)
    monkeypatch.setattr(decide_mod, "MemoryStore", StubMemoryStore)

    config = LumynConfig(
        store_path=clean_store,
        policy_path="policies/starter.v1.yml",
        memory_enabled=True,
        memory_path=tmp_path / "memory",
    )

    request = {
        "schema_version": "decision_request.v1",
        "request_id": "req_v1_test_002",
        "subject": {"type": "service", "id": "test-service", "tenant_id": "acme"},
        "action": {
            "type": "support.refund",
            "intent": "refund test",
            "amount": {"value": 10.0, "currency": "USD"},
        },
        "context": {"mode": "digest_only", "digest": "sha256:" + ("0" * 64)},
        "evidence": {
            "ticket_id": "T-1",
            "order_id": "O-1",
            "customer_id": "C-1",
            "payment_instrument_risk": "low",
            "chargeback_risk": 0.0,
            "previous_refund_count_90d": 0,
            "customer_age_days": 180,
        },
    }

    record = decide_v1(request, config=config)
    memory = record["determinism"]["memory"]
    assert memory["schema_version"] == "memory_snapshot.v1"
    assert memory["snapshot_digest"].startswith("sha256:")
    assert memory["snapshot_digest"] == compute_memory_snapshot_digest_v1(memory)
