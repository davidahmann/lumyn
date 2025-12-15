from __future__ import annotations

import copy
from typing import Any


def verdict_v0_to_v1(verdict_v0: str) -> str:
    """
    Map v0 verdicts to the v1 four-outcome model.

    v0: TRUST | QUERY | ABSTAIN | ESCALATE
    v1: ALLOW | DENY | ABSTAIN | ESCALATE
    """
    if verdict_v0 == "TRUST":
        return "ALLOW"
    if verdict_v0 == "QUERY":
        # v0 QUERY means "deny until evidence"; v1 callers should not take action and should
        # consult `queries` for required fields.
        return "DENY"
    if verdict_v0 in {"ABSTAIN", "ESCALATE"}:
        return verdict_v0
    raise ValueError(f"unknown v0 verdict: {verdict_v0}")


def decision_request_v0_to_v1(request: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(request)
    out["schema_version"] = "decision_request.v1"
    return out


def decision_record_v0_to_v1(record: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(record)
    out["schema_version"] = "decision_record.v1"

    verdict_raw = out.get("verdict")
    verdict = verdict_raw if isinstance(verdict_raw, str) else ""
    out["verdict"] = verdict_v0_to_v1(verdict)

    request_obj = out.get("request")
    if isinstance(request_obj, dict):
        out["request"] = decision_request_v0_to_v1(request_obj)

    return out
