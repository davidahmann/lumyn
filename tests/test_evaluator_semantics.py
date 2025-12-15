from __future__ import annotations

from lumyn.engine.evaluator import evaluate_policy
from lumyn.policy.loader import load_policy


def test_stage_order_and_precedence_query_over_escalate() -> None:
    loaded = load_policy("policies/lumyn-support.v0.yml")
    policy = dict(loaded.policy)

    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "agent", "id": "agent-1", "tenant_id": "acme"},
        "action": {
            "type": "support.refund",
            "intent": "Refund large order but missing evidence",
            "amount": {"value": 201.0, "currency": "USD"},
        },
        "evidence": {"ticket_id": "ZD-1", "customer_id": "C-1"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        },
    }

    result = evaluate_policy(request, policy=policy)
    assert result.verdict == "QUERY"
    assert "MISSING_EVIDENCE_REFUND" in result.reason_codes
    assert any(r.stage == "ESCALATIONS" for r in result.matched_rules)


def test_default_path_is_deterministic() -> None:
    loaded = load_policy("policies/lumyn-support.v0.yml")
    policy = dict(loaded.policy)

    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "agent", "id": "agent-2", "tenant_id": "acme"},
        "action": {"type": "support.unknown_action", "intent": "Unknown action"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }

    result = evaluate_policy(request, policy=policy)
    assert result.verdict == "ESCALATE"
    assert result.reason_codes[-1] == "NO_MATCH_DEFAULT_ESCALATE"
    assert result.matched_rules[-1].stage == "DEFAULT"
