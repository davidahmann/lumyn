from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NormalizedRequestV1:
    action_type: str
    amount_currency: str | None
    amount_value: float | None
    amount_usd: float | None
    evidence: dict[str, object]
    fx_rate_to_usd_present: bool


def _canonical_json_bytes(obj: Any) -> bytes:
    """
    Produce RFC 8785 (JCS) compatible JSON bytes.
    - keys sorted
    - no whitespace
    - ensure_ascii=False
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def normalize_request_v1(request: dict[str, Any]) -> NormalizedRequestV1:
    action = request.get("action") or {}
    evidence_raw = request.get("evidence") or {}

    action_type = str(action.get("type"))
    amount = action.get("amount") or {}

    amount_currency = amount.get("currency")
    if not isinstance(amount_currency, str):
        amount_currency = None

    amount_value_raw = amount.get("value")
    amount_value = float(amount_value_raw) if isinstance(amount_value_raw, (int, float)) else None

    # evidence in v1 is strictly a dict
    evidence: dict[str, object]
    if isinstance(evidence_raw, dict):
        evidence = {str(k): v for k, v in evidence_raw.items()}
    else:
        evidence = {}

    fx_rate_raw = evidence.get("fx_rate_to_usd")
    if isinstance(fx_rate_raw, (int, float)):
        fx_rate_to_usd_present = True
        fx_rate_to_usd: float | None = float(fx_rate_raw)
    else:
        fx_rate_to_usd_present = False
        fx_rate_to_usd = None

    amount_usd: float | None
    if amount_value is None or amount_currency is None:
        amount_usd = None
    elif amount_currency == "USD":
        amount_usd = amount_value
    elif fx_rate_to_usd is not None:
        amount_usd = amount_value * fx_rate_to_usd
    else:
        amount_usd = None

    return NormalizedRequestV1(
        action_type=action_type,
        amount_currency=amount_currency,
        amount_value=amount_value,
        amount_usd=amount_usd,
        evidence=evidence,
        fx_rate_to_usd_present=fx_rate_to_usd_present,
    )


def compute_inputs_digest_v1(request: dict[str, Any], *, normalized: NormalizedRequestV1) -> str:
    """
    Compute the v1 inputs digest.
    Structure:
    {
      "request": <request_json>,
      "derived": {
        "action_type": ...,
        "amount_usd": ...,
        ...
      }
    }
    """
    # Create the payload for digest
    payload = {
        "request": request,
        "derived": {
            "action_type": normalized.action_type,
            "amount_currency": normalized.amount_currency,
            "amount_value": normalized.amount_value,
            "amount_usd": normalized.amount_usd,
            "fx_rate_to_usd_present": normalized.fx_rate_to_usd_present,
            # In v1 we might include normalized evidence keys or similar if needed for strictness,
            # but request is already included. 'derived' captures computed features used in policy.
        },
    }
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"sha256:{digest}"


def compute_memory_snapshot_digest_v1(snapshot: Mapping[str, Any]) -> str:
    """
    Compute a digest for the memory snapshot used during arbitration.

    The digest is computed over the snapshot payload excluding the digest field itself.
    """
    payload = dict(snapshot)
    payload.pop("snapshot_digest", None)
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"sha256:{digest}"


def build_memory_snapshot_v1(
    *,
    projection_model: str,
    query_top_k: int,
    risk_threshold: float,
    success_allow_threshold: float,
    hits: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a deterministic, replayable summary of the memory basis used for arbitration.

    `hits` should contain only fields that affect arbitration and are stable for replay,
    e.g. {"decision_id": "...", "outcome": -1|1, "score": 0.93}.
    """
    normalized_hits: list[dict[str, Any]] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        decision_id = hit.get("decision_id")
        outcome = hit.get("outcome")
        score = hit.get("score")
        if not isinstance(decision_id, str):
            continue
        if not isinstance(outcome, int) or outcome not in (-1, 1):
            continue
        if not isinstance(score, (int, float)):
            continue
        normalized_hits.append(
            {
                "decision_id": decision_id,
                "outcome": int(outcome),
                "score": float(score),
            }
        )

    normalized_hits.sort(key=lambda h: (-h["score"], h["decision_id"], h["outcome"]))

    snapshot = {
        "schema_version": "memory_snapshot.v1",
        "projection": {"model": projection_model},
        "query": {"top_k": int(query_top_k)},
        "consensus": {
            "risk_threshold": float(risk_threshold),
            "success_allow_threshold": float(success_allow_threshold),
        },
        "hits": normalized_hits,
    }
    snapshot["snapshot_digest"] = compute_memory_snapshot_digest_v1(snapshot)
    return snapshot
