from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RedactionResult:
    request: dict[str, Any]
    fields_removed: list[str]
    profile: str


def redact_request_for_persistence(
    request: dict[str, Any],
    *,
    profile: str,
) -> RedactionResult:
    request_out = copy.deepcopy(request)
    profile = profile.strip()
    if profile not in {"default", "strict", "off"}:
        profile = "default"

    context = request_out.get("context")
    if not isinstance(context, dict):
        return RedactionResult(request=request_out, fields_removed=[], profile=profile)

    mode = context.get("mode")
    if mode != "inline":
        _ensure_redaction_meta(context, profile=profile, fields_removed=[])
        return RedactionResult(request=request_out, fields_removed=[], profile=profile)

    inline = context.get("inline")
    if not isinstance(inline, dict):
        _ensure_redaction_meta(context, profile=profile, fields_removed=[])
        return RedactionResult(request=request_out, fields_removed=[], profile=profile)

    if profile == "off":
        _ensure_redaction_meta(context, profile=profile, fields_removed=[])
        return RedactionResult(request=request_out, fields_removed=[], profile=profile)

    removed: list[str] = []

    if profile == "strict":
        for key in sorted(inline.keys(), key=str):
            removed.append(f"/context/inline/{key}")
        context["inline"] = {}
        _ensure_redaction_meta(context, profile=profile, fields_removed=removed)
        return RedactionResult(request=request_out, fields_removed=removed, profile=profile)

    # default: remove likely-sensitive keys under context.inline.
    sensitive_keys = {
        "api_key",
        "authorization",
        "email",
        "messages",
        "password",
        "phone",
        "prompt",
        "raw",
        "ssn",
        "token",
        "access_token",
        "transcript",
    }

    for key in sorted(list(inline.keys()), key=str):
        if str(key).lower() in sensitive_keys:
            removed.append(f"/context/inline/{key}")
            inline.pop(key, None)

    _ensure_redaction_meta(context, profile=profile, fields_removed=removed)
    return RedactionResult(request=request_out, fields_removed=removed, profile=profile)


def _ensure_redaction_meta(
    context: dict[str, Any], *, profile: str, fields_removed: list[str]
) -> None:
    redaction = context.get("redaction")
    if not isinstance(redaction, dict):
        redaction = {}
        context["redaction"] = redaction
    redaction["profile"] = profile
    redaction["fields_removed"] = list(fields_removed)
