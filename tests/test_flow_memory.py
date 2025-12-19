import shutil
from pathlib import Path

from lumyn.core.decide import LumynConfig, decide
from lumyn.engine.normalize_v1 import normalize_request_v1
from lumyn.memory.client import MemoryStore
from lumyn.memory.embed import ProjectionLayer
from lumyn.memory.types import Experience

DB_PATH = Path(".lumyn/test_flow.db")
MEM_PATH = Path(".lumyn/test_memory_flow")


def setup_module() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    if MEM_PATH.exists():
        shutil.rmtree(MEM_PATH)


def teardown_module() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    if MEM_PATH.exists():
        shutil.rmtree(MEM_PATH)


def test_precognition_flow() -> None:
    """
    Test that teaching a failure causes future similar requests to be blocked.
    """
    config = LumynConfig(
        store_path=DB_PATH,
        policy_path="src/lumyn/_data/policies/starter.v1.yml",
        memory_enabled=True,
        memory_path=MEM_PATH,
    )

    # 1. Initial Request (Should be ALLOWed)
    req = {
        "schema_version": "decision_request.v1",
        "action": {
            "type": "support.refund",
            "intent": "request_refund",
            "amount": {"value": 10.0, "currency": "USD"},
        },
        "evidence": {
            "ticket_id": "T-123",
            "order_id": "O-999",
            "customer_id": "C-111",
            "payment_instrument_risk": "low",
            "chargeback_risk": 0.0,
            "previous_refund_count_90d": 0,
            "customer_age_days": 100,
            "user_tier": "gold",
        },
        "policy": {"mode": "enforce"},
        "request_id": "req_001",
        "subject": {"type": "user", "id": "U-123", "tenant_id": "tenant_A"},
        "context": {
            "mode": "inline",
            "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000001",
            "inline": {"source": "test"},
        },
    }

    decision1 = decide(req, config=config)
    assert decision1["verdict"] == "ALLOW", f"Initial decision failed: {decision1['reason_codes']}"

    # 2. Teach Memory (Simulate 'lumyn learn')
    # Use the same request to generate exact vector + failure outcome
    norm = normalize_request_v1(decision1["request"])
    proj = ProjectionLayer()
    vector = proj.embed_request(norm)

    exp = Experience(
        decision_id="req_001",
        vector=vector,
        outcome=-1,  # FAILURE
        severity=5,
        original_verdict="ALLOW",
        timestamp="now",
    )
    mem_store = MemoryStore(db_path=MEM_PATH)
    mem_store.add_experiences([exp])

    # 3. New Request (Similar/Identical)
    # Should now be ABSTAIN due to risk
    req2 = req.copy()
    req2["request_id"] = "req_002"

    decision2 = decide(req2, config=config)

    assert decision2["verdict"] == "ABSTAIN"
    assert "FAILURE_MEMORY_SIMILAR_BLOCK" in decision2["reason_codes"]

    # Check risk signals
    assert decision2["risk_signals"]["failure_similarity"]["score"] > 0.99
    assert decision2["risk_signals"]["failure_similarity"]["top_k"][0]["label"] == "failure"
