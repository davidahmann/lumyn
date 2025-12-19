from __future__ import annotations

import copy
import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from lumyn.engine.consensus import ConsensusEngine
from lumyn.engine.evaluator import EvaluationResult, evaluate_policy
from lumyn.engine.evaluator_v1 import EvaluationResultV1, evaluate_policy_v1
from lumyn.engine.normalize import normalize_request
from lumyn.engine.normalize_v1 import compute_inputs_digest_v1, normalize_request_v1
from lumyn.engine.redaction import redact_request_for_persistence
from lumyn.engine.similarity import top_k_matches
from lumyn.memory.client import MemoryStore
from lumyn.memory.embed import ProjectionLayer
from lumyn.policy.loader import LoadedPolicy, load_policy, read_policy_text
from lumyn.records.emit import RiskSignals, build_decision_record, compute_inputs_digest
from lumyn.records.emit_v1 import RiskSignalsV1, build_decision_record_v1
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
    memory_enabled: bool = True
    memory_path: str | Path = ".lumyn/memory"


def _validate_request_or_raise(request: dict[str, Any]) -> None:
    schema = load_json_schema("schemas/decision_request.v0.schema.json")
    Draft202012Validator(schema).validate(request)


def _is_storage_error(exc: Exception) -> bool:
    return isinstance(exc, (OSError, sqlite3.Error))


def _abstain_storage_unavailable_record(
    *,
    request_for_record: dict[str, Any],
    loaded_policy: Any,
    inputs_digest: str,
) -> dict[str, Any]:
    return build_decision_record(
        request=request_for_record,
        loaded_policy=loaded_policy,
        evaluation=EvaluationResult(
            verdict="ABSTAIN",
            reason_codes=["STORAGE_UNAVAILABLE"],
            matched_rules=[],
            queries=[],
            obligations=[],
        ),
        inputs_digest=inputs_digest,
        risk_signals=RiskSignals(
            uncertainty_score=1.0,
            failure_similarity_score=0.0,
            failure_similarity_top_k=[],
        ),
        engine_version=__version__,
    )


def _abstain_storage_unavailable_record_v1(
    *,
    request_for_record: dict[str, Any],
    loaded_policy: Any,
    inputs_digest: str,
) -> dict[str, Any]:
    return build_decision_record_v1(
        request=request_for_record,
        loaded_policy=loaded_policy,
        evaluation=EvaluationResultV1(
            verdict="ABSTAIN",
            reason_codes=["STORAGE_UNAVAILABLE"],
            matched_rules=[],
            queries=[],
            obligations=[],
        ),
        inputs_digest=inputs_digest,
        risk_signals=RiskSignalsV1(
            uncertainty_score=1.0,
            failure_similarity_score=0.0,
            failure_similarity_top_k=[],
            success_similarity_score=0.0,
            success_similarity_top_k=[],
        ),
        engine_version=__version__,
    )


def _validate_request_v1_or_raise(request: dict[str, Any]) -> None:
    schema = load_json_schema("schemas/decision_request.v1.schema.json")
    Draft202012Validator(schema).validate(request)


def decide_v0(
    request: dict[str, Any],
    *,
    config: LumynConfig | None = None,
    store: SqliteStore | None = None,
    loaded_policy: LoadedPolicy | None = None,
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

        if loaded_policy is None:
            loaded_policy = load_policy(cfg.policy_path)
        policy = dict(loaded_policy.policy)

        normalized = normalize_request(request_eval)

        tenant_id = (
            request_eval.get("subject", {}).get("tenant_id")
            if isinstance(request_eval.get("subject"), dict)
            else None
        )
        tenant_id = tenant_id if isinstance(tenant_id, str) else None

        redaction_profile = cfg.redaction_profile
        ctx = request_eval.get("context")
        if isinstance(ctx, dict):
            redaction = ctx.get("redaction")
            if isinstance(redaction, dict) and isinstance(redaction.get("profile"), str):
                redaction_profile = redaction["profile"]

        store_impl = store or SqliteStore(cfg.store_path)
        try:
            store_impl.init()
            store_impl.put_policy_snapshot(
                policy_hash=loaded_policy.policy_hash,
                policy_id=str(loaded_policy.policy["policy_id"]),
                policy_version=str(loaded_policy.policy["policy_version"]),
                policy_text=read_policy_text(cfg.policy_path),
            )
        except Exception as e:
            if _is_storage_error(e):
                request_for_record = copy.deepcopy(request_eval)
                redaction_result = redact_request_for_persistence(
                    request_for_record, profile=redaction_profile
                )
                inputs_digest = compute_inputs_digest(
                    redaction_result.request, normalized=normalized
                )
                record = _abstain_storage_unavailable_record(
                    request_for_record=redaction_result.request,
                    loaded_policy=loaded_policy,
                    inputs_digest=inputs_digest,
                )
                log_decision_record(record)
                return record
            raise

        request_id = (
            request_eval.get("request_id")
            if isinstance(request_eval.get("request_id"), str)
            else None
        )
        tenant_key = tenant_id or "__global__"
        if request_id is not None:
            existing_id = store_impl.get_decision_id_for_request_id(
                tenant_key=tenant_key, request_id=request_id
            )
            if existing_id is not None:
                existing = store_impl.get_decision_record(existing_id)
                if existing is not None:
                    log_decision_record(existing)
                    return existing

        # Experience memory similarity (MVP): compare feature dicts.
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

        matches = top_k_matches(query_feature=query_feature, candidates=candidates, top_k=cfg.top_k)
        failure_matches = [m for m in matches if m.label == "failure"]
        failure_similarity_score = failure_matches[0].score if failure_matches else 0.0

        evidence_obj = request_eval.get("evidence")
        evidence: dict[str, Any]
        if isinstance(evidence_obj, dict):
            evidence = evidence_obj
        else:
            evidence = {}
            request_eval["evidence"] = evidence
        evidence["failure_similarity_score"] = float(failure_similarity_score)

        evaluation = evaluate_policy(request_eval, policy=policy)

        # Uncertainty MVP: deterministic heuristic.
        uncertainty = 0.2
        if evaluation.verdict == "QUERY":
            uncertainty += 0.2
        if failure_similarity_score >= 0.35:
            uncertainty += 0.3
        uncertainty = min(1.0, max(0.0, uncertainty))

        request_for_record = copy.deepcopy(request_eval)
        redaction_result = redact_request_for_persistence(
            request_for_record, profile=redaction_profile
        )
        inputs_digest = compute_inputs_digest(redaction_result.request, normalized=normalized)

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
        try:
            store_impl.put_decision_record(record)
        except Exception as e:
            if isinstance(e, sqlite3.IntegrityError) and request_id is not None:
                existing_id = store_impl.get_decision_id_for_request_id(
                    tenant_key=tenant_key,
                    request_id=request_id,
                )
                if existing_id is not None:
                    existing = store_impl.get_decision_record(existing_id)
                    if existing is not None:
                        log_decision_record(existing)
                        return existing
            if _is_storage_error(e):
                record = _abstain_storage_unavailable_record(
                    request_for_record=redaction_result.request,
                    loaded_policy=loaded_policy,
                    inputs_digest=inputs_digest,
                )
                log_decision_record(record)
                return record
            raise

        log_decision_record(record)
        return record


# Backward compatibility alias
def decide(
    request: dict[str, Any],
    *,
    config: LumynConfig | None = None,
    store: SqliteStore | None = None,
    loaded_policy: LoadedPolicy | None = None,
) -> dict[str, Any]:
    cfg = config or LumynConfig()

    if loaded_policy is None:
        # Load policy once to determine version
        try:
            loaded_policy = load_policy(cfg.policy_path)
        except Exception:
            # If loading fails, let v0 handle it (or fail inside v0 path)
            # But v0 path creates defaults if missing?
            # Actually load_policy raises if file missing/invalid.
            # But decide_v0 handles FileNotFoundError?
            # No, decide_v0 calls load_policy which expects file handling.
            # Let's just raise here if it fails, consistent with previous behavior.
            raise

    version = loaded_policy.policy.get("schema_version", "policy.v0")
    if version.startswith("policy.v1"):
        return decide_v1(request, config=config, store=store, loaded_policy=loaded_policy)
    else:
        return decide_v0(request, config=config, store=store, loaded_policy=loaded_policy)


def decide_v1(
    request: dict[str, Any],
    *,
    config: LumynConfig | None = None,
    store: SqliteStore | None = None,
    loaded_policy: LoadedPolicy | None = None,
) -> dict[str, Any]:
    cfg = config or LumynConfig()
    with start_span("lumyn.decide_v1", attributes={"top_k": cfg.top_k}):
        request_eval = copy.deepcopy(request)
        if cfg.mode in {"enforce", "advisory"}:
            policy_obj = request_eval.get("policy")
            if isinstance(policy_obj, dict):
                policy_obj.setdefault("mode", cfg.mode)
            else:
                request_eval["policy"] = {"mode": cfg.mode}

        _validate_request_v1_or_raise(request_eval)

        if loaded_policy is None:
            loaded_policy = load_policy(cfg.policy_path)
        policy = dict(loaded_policy.policy)

        normalized = normalize_request_v1(request_eval)

        tenant_id = (
            request_eval.get("subject", {}).get("tenant_id")
            if isinstance(request_eval.get("subject"), dict)
            else None
        )
        tenant_id = tenant_id if isinstance(tenant_id, str) else None

        redaction_profile = cfg.redaction_profile
        ctx = request_eval.get("context")
        if isinstance(ctx, dict):
            redaction = ctx.get("redaction")
            if isinstance(redaction, dict) and isinstance(redaction.get("profile"), str):
                redaction_profile = redaction["profile"]

        store_impl = store or SqliteStore(cfg.store_path)
        try:
            store_impl.init()
            # Store policy snapshot - unchanged for v1 (policy text is same)
            store_impl.put_policy_snapshot(
                policy_hash=loaded_policy.policy_hash,
                policy_id=str(loaded_policy.policy["policy_id"]),
                policy_version=str(loaded_policy.policy["policy_version"]),
                policy_text=read_policy_text(cfg.policy_path),
            )
        except Exception as e:
            if _is_storage_error(e):
                request_for_record = copy.deepcopy(request_eval)
                redaction_result = redact_request_for_persistence(
                    request_for_record, profile=redaction_profile
                )
                inputs_digest = compute_inputs_digest_v1(
                    redaction_result.request, normalized=normalized
                )
                record = _abstain_storage_unavailable_record_v1(
                    request_for_record=redaction_result.request,
                    loaded_policy=loaded_policy,
                    inputs_digest=inputs_digest,
                )
                log_decision_record(record)
                return record
            raise

        request_id = (
            request_eval.get("request_id")
            if isinstance(request_eval.get("request_id"), str)
            else None
        )
        tenant_key = tenant_id or "__global__"
        if request_id is not None:
            existing_id = store_impl.get_decision_id_for_request_id(
                tenant_key=tenant_key, request_id=request_id
            )
            if existing_id is not None:
                existing = store_impl.get_decision_record(existing_id)
                if existing is not None:
                    # Note: existing record might be v0 or v1.
                    # Ideally we verify schema version? For now return as is.
                    log_decision_record(existing)
                    return existing

        # Experience memory similarity (BEM Integration)
        failure_similarity_score = 0.0
        success_similarity_score = 0.0
        memory_hits = []

        if cfg.memory_enabled:
            # 1. Project
            proj = ProjectionLayer()
            vector = proj.embed_request(normalized)

            # 2. Search
            mem_store = MemoryStore(db_path=cfg.memory_path)
            memory_hits = mem_store.search(vector, limit=cfg.top_k)

            # 3. Arbitrate (Consensus Engine)
            # Eval happens first? Yes, eval provides Heuristic input.

        evaluation = evaluate_policy_v1(request_eval, policy=policy)

        uncertainty = 0.2
        if cfg.memory_enabled:
            # Calculate Risk Signal for metadata
            for h in memory_hits:
                if h.experience.outcome == -1 and h.score > failure_similarity_score:
                    failure_similarity_score = h.score
                if h.experience.outcome == 1 and h.score > success_similarity_score:
                    success_similarity_score = h.score

            ce = ConsensusEngine()
            consensus = ce.arbitrate(evaluation, memory_hits)

            # Update Verdict if Consensus changed it
            if consensus.verdict != evaluation.verdict:
                new_reasons = list(evaluation.reason_codes)
                if consensus.reason:
                    new_reasons.append(consensus.reason)

                evaluation = replace(
                    evaluation, verdict=consensus.verdict, reason_codes=new_reasons
                )

            # Use uncertainty from Consensus Engine (driven by memory signals)
            uncertainty = consensus.uncertainty

        # Legacy fallback for non-memory path
        if not cfg.memory_enabled:
            if evaluation.verdict == "DENY":
                uncertainty = 0.4  # Moderate uncertainty without memory context
            else:
                uncertainty = 0.5  # Default: no memory = no context = uncertain
        uncertainty = min(1.0, max(0.0, uncertainty))

        request_for_record = copy.deepcopy(request_eval)
        redaction_result = redact_request_for_persistence(
            request_for_record, profile=redaction_profile
        )
        inputs_digest = compute_inputs_digest_v1(redaction_result.request, normalized=normalized)

        record = build_decision_record_v1(
            request=redaction_result.request,
            loaded_policy=loaded_policy,
            evaluation=evaluation,
            inputs_digest=inputs_digest,
            risk_signals=RiskSignalsV1(
                uncertainty_score=uncertainty,
                failure_similarity_score=failure_similarity_score,
                failure_similarity_top_k=[
                    {
                        "id": h.experience.decision_id,
                        "label": "failure",
                        "score": h.score,
                        "summary": f"Similarity {h.score:.2f}",
                    }
                    for h in memory_hits
                    if h.experience.outcome == -1
                ],
                success_similarity_score=success_similarity_score,
                success_similarity_top_k=[
                    {
                        "id": h.experience.decision_id,
                        "label": "success",
                        "score": h.score,
                        "summary": f"Similarity {h.score:.2f}",
                    }
                    for h in memory_hits
                    if h.experience.outcome == 1
                ],
            ),
            engine_version=__version__,
        )

        try:
            store_impl.put_decision_record(record)
        except Exception as e:
            if isinstance(e, sqlite3.IntegrityError) and request_id is not None:
                existing_id = store_impl.get_decision_id_for_request_id(
                    tenant_key=tenant_key,
                    request_id=request_id,
                )
                if existing_id is not None:
                    existing = store_impl.get_decision_record(existing_id)
                    if existing is not None:
                        log_decision_record(existing)
                        return existing
            if _is_storage_error(e):
                record = _abstain_storage_unavailable_record_v1(
                    request_for_record=redaction_result.request,
                    loaded_policy=loaded_policy,
                    inputs_digest=inputs_digest,
                )
                log_decision_record(record)
                return record
            raise

        log_decision_record(record)
        return record
