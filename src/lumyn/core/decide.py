from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from lumyn.engine.evaluator import evaluate_policy
from lumyn.engine.normalize import normalize_request
from lumyn.engine.redaction import redact_request_for_persistence
from lumyn.engine.similarity import top_k_matches
from lumyn.policy.loader import load_policy
from lumyn.records.emit import RiskSignals, build_decision_record, compute_inputs_digest
from lumyn.schemas.loaders import load_json_schema
from lumyn.store.sqlite import SqliteStore
from lumyn.telemetry.logging import log_decision_record
from lumyn.telemetry.tracing import start_span
from lumyn.version import __version__


@dataclass(frozen=True, slots=True)
class LumynConfig:
    policy_path: str | Path = "policies/lumyn-support.v0.yml"
    store_path: str | Path = ".lumyn/lumyn.db"
    top_k: int = 5
    mode: str | None = None
    redaction_profile: str = "default"


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
    with start_span("lumyn.decide", attributes={"top_k": cfg.top_k}):
        request_eval = copy.deepcopy(request)
        if cfg.mode in {"enforce", "advisory"}:
            policy_obj = request_eval.get("policy")
            if isinstance(policy_obj, dict):
                policy_obj.setdefault("mode", cfg.mode)
            else:
                request_eval["policy"] = {"mode": cfg.mode}

        _validate_request_or_raise(request_eval)

        loaded_policy = load_policy(cfg.policy_path)
        policy = dict(loaded_policy.policy)

        normalized = normalize_request(request_eval)

        store_impl = store or SqliteStore(cfg.store_path)
        store_impl.init()
        store_impl.put_policy_snapshot(
            policy_hash=loaded_policy.policy_hash,
            policy_id=str(loaded_policy.policy["policy_id"]),
            policy_version=str(loaded_policy.policy["policy_version"]),
            policy_text=Path(cfg.policy_path).read_text(encoding="utf-8"),
        )

        # Experience memory similarity (MVP): compare feature dicts.
        tenant_id = (
            request_eval.get("subject", {}).get("tenant_id")
            if isinstance(request_eval.get("subject"), dict)
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
            "tags": (
                request_eval.get("action", {})
                if isinstance(request_eval.get("action"), dict)
                else {}
            ).get("tags", []),
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

        evaluation = evaluate_policy(request_eval, policy=policy)

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

        inputs_digest = compute_inputs_digest(request_eval, normalized=normalized)

        redaction_profile = cfg.redaction_profile
        ctx = request_eval.get("context")
        if isinstance(ctx, dict):
            redaction = ctx.get("redaction")
            if isinstance(redaction, dict) and isinstance(redaction.get("profile"), str):
                redaction_profile = redaction["profile"]

        request_for_record = copy.deepcopy(request_eval)
        redaction_result = redact_request_for_persistence(
            request_for_record, profile=redaction_profile
        )

        record = build_decision_record(
            request=redaction_result.request,
            loaded_policy=loaded_policy,
            evaluation=evaluation,
            inputs_digest=inputs_digest,
            risk_signals=RiskSignals(
                uncertainty_score=uncertainty,
                failure_similarity_score=failure_similarity_score,
                failure_similarity_top_k=[
                    {
                        "memory_id": m.memory_id,
                        "label": m.label,
                        "score": m.score,
                        "summary": m.summary,
                    }
                    for m in matches
                ],
            ),
            engine_version=__version__,
        )

        # Persist before returning (MVP contract).
        store_impl.put_decision_record(record)
        log_decision_record(record)
        return record
