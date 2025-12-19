from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import ulid

from lumyn.policy.spec import LoadedPolicy

# We might redefine MatchedRule if we want strict typing on 'effect' (ALLOW/DENY vs TRUST/QUERY)
# For now, let's redefine it to be safe and explicit about v1 verdicts.


@dataclass(frozen=True, slots=True)
class MatchedRuleV1:
    rule_id: str
    stage: str
    effect: str
    reason_codes: list[str]


@dataclass(frozen=True, slots=True)
class EvaluationResultV1:
    verdict: str
    reason_codes: list[str]
    matched_rules: list[MatchedRuleV1]
    queries: list[dict[str, str]]
    obligations: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class RiskSignalsV1:
    uncertainty_score: float
    failure_similarity_score: float
    failure_similarity_top_k: list[dict[str, Any]]
    success_similarity_score: float
    success_similarity_top_k: list[dict[str, Any]]


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _matched_rule_to_record(rule: MatchedRuleV1) -> dict[str, Any]:
    return {
        "rule_id": rule.rule_id,
        "stage": rule.stage,
        "effect": rule.effect,
        "reason_codes": rule.reason_codes,
    }


def build_decision_record_v1(
    *,
    request: dict[str, Any],
    loaded_policy: LoadedPolicy,
    evaluation: EvaluationResultV1,
    inputs_digest: str,
    risk_signals: RiskSignalsV1,
    engine_version: str,
) -> dict[str, Any]:
    policy = loaded_policy.policy
    mode = (request.get("policy", {}) if isinstance(request.get("policy"), dict) else {}).get(
        "mode", policy["defaults"]["mode"]
    )
    # v1 policy also supports "enforce" | "advisory"
    if mode not in {"enforce", "advisory"}:
        mode = policy["defaults"]["mode"]

    record = {
        "schema_version": "decision_record.v1",
        "decision_id": str(ulid.new()),
        "created_at": _utc_now_iso(),
        "trace": request.get("trace", {}) or {},  # Default to empty dict if None
        "request": request,
        "policy": {
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "policy_hash": loaded_policy.policy_hash,
            "mode": mode,
        },
        "verdict": evaluation.verdict,
        "reason_codes": evaluation.reason_codes,
        "matched_rules": [_matched_rule_to_record(r) for r in evaluation.matched_rules],
        "risk_signals": {
            "uncertainty_score": risk_signals.uncertainty_score,
            "failure_similarity": {
                "score": risk_signals.failure_similarity_score,
                "top_k": risk_signals.failure_similarity_top_k,
            },
            "success_similarity": {
                "score": risk_signals.success_similarity_score,
                "top_k": risk_signals.success_similarity_top_k,
            },
        },
        "queries": evaluation.queries,
        "obligations": evaluation.obligations,
        "determinism": {
            "engine_version": engine_version,
            "evaluation_order": [
                "REQUIREMENTS",
                "HARD_BLOCKS",
                "ESCALATIONS",
                "ALLOW_PATHS",
                "DEFAULT",
            ],
            # v1 Determinism: inputs_digest allows verifying the state of the world
            # (policy + request) at decision time.
            "inputs_digest": inputs_digest,
        },
        "extensions": {},
    }
    return record
