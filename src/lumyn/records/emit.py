from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import ulid

from lumyn.engine.evaluator import EvaluationResult, MatchedRule
from lumyn.engine.normalize import NormalizedRequest
from lumyn.policy.spec import LoadedPolicy


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def compute_inputs_digest(request: dict[str, Any], *, normalized: NormalizedRequest) -> str:
    # v0: include request + derived fields that affect evaluation. Keep deterministic.
    payload = {
        "request": request,
        "derived": {
            "action_type": normalized.action_type,
            "amount_currency": normalized.amount_currency,
            "amount_value": normalized.amount_value,
            "amount_usd": normalized.amount_usd,
            "fx_rate_to_usd_present": normalized.fx_rate_to_usd_present,
        },
    }
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"sha256:{digest}"


def _matched_rule_to_record(rule: MatchedRule) -> dict[str, Any]:
    return {
        "rule_id": rule.rule_id,
        "stage": rule.stage,
        "effect": rule.effect,
        "reason_codes": rule.reason_codes,
    }


@dataclass(frozen=True, slots=True)
class RiskSignals:
    uncertainty_score: float
    failure_similarity_score: float
    failure_similarity_top_k: list[dict[str, Any]]


def build_decision_record(
    *,
    request: dict[str, Any],
    loaded_policy: LoadedPolicy,
    evaluation: EvaluationResult,
    inputs_digest: str,
    risk_signals: RiskSignals,
    engine_version: str,
) -> dict[str, Any]:
    policy = loaded_policy.policy
    mode = (request.get("policy", {}) if isinstance(request.get("policy"), dict) else {}).get(
        "mode", policy["defaults"]["mode"]
    )
    if mode not in {"enforce", "advisory"}:
        mode = policy["defaults"]["mode"]

    record = {
        "schema_version": "decision_record.v0",
        "decision_id": str(ulid.new()),
        "created_at": _utc_now_iso(),
        "trace": request.get("trace", {}),
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
        },
        "queries": evaluation.queries,
        "obligations": evaluation.obligations,
        "determinism": {
            "engine_version": engine_version,
            "evaluation_order": [
                "REQUIREMENTS",
                "HARD_BLOCKS",
                "ESCALATIONS",
                "TRUST_PATHS",
                "DEFAULT",
            ],
            "inputs_digest": inputs_digest,
        },
        "extensions": {},
    }
    return record
