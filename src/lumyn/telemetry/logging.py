from __future__ import annotations

import json
import logging
import os
from typing import Any


def configure_logging(*, level: str | None = None) -> None:
    raw_level = level or os.getenv("LUMYN_LOG_LEVEL") or "INFO"
    level_name = raw_level.upper()
    log_level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )


def _safe_record_summary(record: dict[str, Any]) -> dict[str, Any]:
    raw_policy = record.get("policy")
    policy: dict[str, Any]
    if isinstance(raw_policy, dict):
        policy = raw_policy
    else:
        policy = {}

    raw_determinism = record.get("determinism")
    determinism: dict[str, Any]
    if isinstance(raw_determinism, dict):
        determinism = raw_determinism
    else:
        determinism = {}

    raw_request = record.get("request")
    request: dict[str, Any]
    if isinstance(raw_request, dict):
        request = raw_request
    else:
        request = {}

    raw_context = request.get("context")
    context: dict[str, Any]
    if isinstance(raw_context, dict):
        context = raw_context
    else:
        context = {}

    return {
        "event": "decision_record",
        "decision_id": record.get("decision_id"),
        "created_at": record.get("created_at"),
        "verdict": record.get("verdict"),
        "reason_codes": record.get("reason_codes", []),
        "policy_hash": policy.get("policy_hash"),
        "policy_id": policy.get("policy_id"),
        "policy_version": policy.get("policy_version"),
        "context_mode": context.get("mode"),
        "context_digest": context.get("digest"),
        "inputs_digest": determinism.get("inputs_digest"),
    }


def log_decision_record(record: dict[str, Any], *, logger: logging.Logger | None = None) -> None:
    logger = logger or logging.getLogger("lumyn")
    payload = _safe_record_summary(record)
    logger.info(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
