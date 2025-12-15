from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from lumyn.engine.evaluator import evaluate_policy
from lumyn.engine.normalize import normalize_request
from lumyn.engine.similarity import top_k_matches
from lumyn.policy.loader import load_policy
from lumyn.records.emit import RiskSignals, build_decision_record, compute_inputs_digest
from lumyn.schemas.loaders import load_json_schema
from lumyn.store.sqlite import SqliteStore
from lumyn.version import __version__


@dataclass(frozen=True, slots=True)
class LumynConfig:
    policy_path: str | Path = "policies/lumyn-support.v0.yml"
    store_path: str | Path = ".lumyn/lumyn.db"
    top_k: int = 5


def _validate_request_or_raise(request: dict[str, Any]) -> None:
    schema = load_json_schema("schemas/decision_request.v0.schema.json")
    Draft202012Validator(schema).validate(request)


def decide(
    request: dict[str, Any],
    *,
    config: LumynConfig | None = None,
    store: SqliteStore | None = None,
) -> dict[str, Any]:
    cfg = config or LumynConfig()
    _validate_request_or_raise(request)

    loaded_policy = load_policy(cfg.policy_path)
    policy = dict(loaded_policy.policy)

    normalized = normalize_request(request)

    store_impl = store or SqliteStore(cfg.store_path)
    store_impl.init()

    # Experience memory similarity (MVP): compare feature dicts.
    tenant_id = (
        request.get("subject", {}).get("tenant_id")
        if isinstance(request.get("subject"), dict)
        else None
    )
    tenant_id = tenant_id if isinstance(tenant_id, str) else None

    query_feature = {
        "action_type": normalized.action_type,
        "amount_currency": normalized.amount_currency,
        "amount_usd_bucket": (
            None
            if normalized.amount_usd is None
            else (
                "small"
                if normalized.amount_usd < 50
                else "medium"
                if normalized.amount_usd < 200
                else "large"
            )
        ),
        "tags": (request.get("action", {}) if isinstance(request.get("action"), dict) else {}).get(
            "tags", []
        ),
    }

    memory_items = store_impl.list_memory_items(
        tenant_id=tenant_id, action_type=normalized.action_type, limit=500
    )
    candidates: list[dict[str, Any]] = []
    for item in memory_items:
        candidates.append(
            {
                "memory_id": item.memory_id,
                "label": item.label,
                "feature": item.feature,
                "summary": item.summary,
            }
        )

    evaluation = evaluate_policy(request, policy=policy)

    matches = top_k_matches(query_feature=query_feature, candidates=candidates, top_k=cfg.top_k)
    failure_matches = [m for m in matches if m.label == "failure"]
    failure_similarity_score = failure_matches[0].score if failure_matches else 0.0

    # Uncertainty MVP: deterministic heuristic.
    uncertainty = 0.2
    if evaluation.verdict == "QUERY":
        uncertainty += 0.2
    if failure_similarity_score >= 0.35:
        uncertainty += 0.3
    uncertainty = min(1.0, max(0.0, uncertainty))

    inputs_digest = compute_inputs_digest(request, normalized=normalized)

    record = build_decision_record(
        request=request,
        loaded_policy=loaded_policy,
        evaluation=evaluation,
        inputs_digest=inputs_digest,
        risk_signals=RiskSignals(
            uncertainty_score=uncertainty,
            failure_similarity_score=failure_similarity_score,
            failure_similarity_top_k=[
                {"memory_id": m.memory_id, "label": m.label, "score": m.score, "summary": m.summary}
                for m in matches
            ],
        ),
        engine_version=__version__,
    )

    # Persist before returning (MVP contract).
    store_impl.put_decision_record(record)
    return record
