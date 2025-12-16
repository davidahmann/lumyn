from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from lumyn.policy.errors import PolicyError
from lumyn.schemas.loaders import load_json_schema

SUPPORTED_WHEN_KEYS = {"action_type", "action_type_in"}

SUPPORTED_CONDITION_KEYS = {
    "amount_usd_gt",
    "amount_usd_gte",
    "amount_usd_lt",
    "amount_usd_lte",
    "amount_currency_is",
    "amount_currency_ne",
    "evidence.fx_rate_to_usd_present",
    "evidence.payment_instrument_risk_is",
    "evidence.payment_instrument_risk_in",
    "evidence.chargeback_risk_gte",
    "evidence.chargeback_risk_lt",
    "evidence.previous_refund_count_90d_gte",
    "evidence.previous_refund_count_90d_lt",
    "evidence.customer_age_days_lt",
    "evidence.customer_age_days_gte",
    "evidence.account_takeover_risk_gte",
    "evidence.failure_similarity_score_gte",
    "evidence.manual_approval_is",
}

# v1 Strict Keys
V1_SUPPORTED_KEYS = {
    "action_type",
    "amount_currency",
    "amount_currency_ne",
    "amount_usd",
    "amount_usd_gt",
    "amount_usd_gte",
    "amount_usd_lt",
    "amount_usd_lte",
}

V1_EVIDENCE_SUFFIXES = {"_is", "_ne", "_in", "_gt", "_gte", "_lt", "_lte"}


@dataclass(frozen=True, slots=True)
class PolicyValidationResult:
    ok: bool
    errors: list[str]


def _validate_rule_expr(rule_id: str, expr: Any, errors: list[str]) -> None:
    if expr is None:
        return
    if not isinstance(expr, Mapping):
        errors.append(f"rule {rule_id}: expression must be an object")
        return
    for key in expr.keys():
        if key not in SUPPORTED_CONDITION_KEYS:
            errors.append(f"rule {rule_id}: unsupported condition key: {key}")


def _validate_v1_rule_expr(rule_id: str, expr: Any, errors: list[str]) -> None:
    if expr is None:
        return
    if not isinstance(expr, Mapping):
        errors.append(f"rule {rule_id}: expression must be an object")
        return
    for key in expr.keys():
        if key in V1_SUPPORTED_KEYS:
            continue

        if key.startswith("evidence."):
            # Check suffix
            # e.g. evidence.foo_bar_gt
            parts = key.rsplit("_", 1)
            if len(parts) == 2:
                suffix = "_" + parts[1]
                if suffix in V1_EVIDENCE_SUFFIXES:
                    continue

            # Special case for exact match on 'evidence.<key>'?
            # v1 spec says explicit operators preferred, but evaluator supports raw lookup (danger).
            # Let's be strict: MUST use operator suffix or be in allowlist.
            # But wait, what if the key is just 'evidence.foo'? Evaluator returns values.
            # Evaluator `_eval_condition` returns False if no operator matches, EXCEPT...
            # Wait, `_eval_condition` in v1 checks suffixes.
            # If key starts with evidence, it splits by `_`.

            errors.append(
                f"rule {rule_id}: unsupported condition key: {key} "
                f"(must end in {', '.join(V1_EVIDENCE_SUFFIXES)})"
            )
            continue

        errors.append(f"rule {rule_id}: unsupported condition key: {key}")


def _validate_when(rule_id: str, when: Any, errors: list[str]) -> None:
    if when is None:
        return
    if not isinstance(when, Mapping):
        errors.append(f"rule {rule_id}: when must be an object")
        return
    for key in when.keys():
        if key not in SUPPORTED_WHEN_KEYS:
            errors.append(f"rule {rule_id}: unsupported when key: {key}")


def validate_policy_v0(
    policy: Mapping[str, Any],
    *,
    policy_schema: Mapping[str, Any],
    known_reason_codes: Iterable[str],
) -> PolicyValidationResult:
    errors: list[str] = []

    validator = Draft202012Validator(policy_schema)
    for err in sorted(validator.iter_errors(policy), key=str):
        errors.append(err.message)

    known = set(known_reason_codes)
    default_reason_code = (
        policy.get("defaults", {}) if isinstance(policy.get("defaults", {}), Mapping) else {}
    ).get("default_reason_code")
    if isinstance(default_reason_code, str) and default_reason_code not in known:
        errors.append(f"unknown default_reason_code: {default_reason_code}")

    rules = policy.get("rules", [])
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, Mapping):
                errors.append("rule must be an object")
                continue

            rule_id = str(rule.get("id", "<missing id>"))
            _validate_when(rule_id, rule.get("when"), errors)

            _validate_rule_expr(rule_id, rule.get("if"), errors)
            if_all = rule.get("if_all", [])
            if if_all is not None:
                if not isinstance(if_all, list):
                    errors.append(f"rule {rule_id}: if_all must be a list")
                else:
                    for expr in if_all:
                        _validate_rule_expr(rule_id, expr, errors)

            if_any = rule.get("if_any", [])
            if if_any is not None:
                if not isinstance(if_any, list):
                    errors.append(f"rule {rule_id}: if_any must be a list")
                else:
                    for expr in if_any:
                        _validate_rule_expr(rule_id, expr, errors)

            then = rule.get("then")
            if not isinstance(then, Mapping):
                continue
            reason_codes = then.get("reason_codes", [])
            if isinstance(reason_codes, list):
                for code in reason_codes:
                    if isinstance(code, str) and code not in known:
                        errors.append(f"rule {rule_id}: unknown reason code: {code}")
            else:
                errors.append(f"rule {rule_id}: then.reason_codes must be a list")

    return PolicyValidationResult(ok=(len(errors) == 0), errors=errors)


def validate_policy_v1(
    policy: Mapping[str, Any],
    *,
    policy_schema: Mapping[str, Any] | None = None,
) -> PolicyValidationResult:
    errors: list[str] = []

    if policy_schema:
        validator = Draft202012Validator(policy_schema)
        for err in sorted(validator.iter_errors(policy), key=str):
            errors.append(err.message)

    # v1 Reason codes: Is there a controlled vocabulary?
    # Spec says: "Reason codes are strings." No strict enum enforcement in v1.0.0 (open world).

    rules = policy.get("rules", [])
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, Mapping):
                continue  # Schema catches this

            rule_id = str(rule.get("id", "<missing id>"))

            # When
            _validate_when(rule_id, rule.get("when"), errors)

            # Conditions
            _validate_v1_rule_expr(rule_id, rule.get("if"), errors)

            if_all = rule.get("if_all")
            if isinstance(if_all, list):
                for expr in if_all:
                    _validate_v1_rule_expr(rule_id, expr, errors)

            if_any = rule.get("if_any")
            if isinstance(if_any, list):
                for expr in if_any:
                    _validate_v1_rule_expr(rule_id, expr, errors)

            # Obligations check?
            # Schema handles structure.

    return PolicyValidationResult(ok=(len(errors) == 0), errors=errors)


def validate_policy_or_raise(
    policy: Mapping[str, Any],
    *,
    policy_schema_path: str | Path,
    reason_codes_path: str | Path | None = None,
) -> None:
    policy_schema = load_json_schema(policy_schema_path)

    schema_version = policy.get("schema_version", "policy.v0")

    if schema_version.startswith("policy.v1"):
        result = validate_policy_v1(policy, policy_schema=policy_schema)
    else:
        # v0 logic
        if not reason_codes_path:
            # Should not happen for v0 defaults
            raise PolicyError("Reason codes path required for v0 validation")

        reason_codes_doc = load_json_schema(reason_codes_path)
        known_reason_codes = [item["code"] for item in reason_codes_doc.get("codes", [])]

        result = validate_policy_v0(
            policy, policy_schema=policy_schema, known_reason_codes=known_reason_codes
        )

    if result.ok:
        return
    raise PolicyError("invalid policy:\n- " + "\n- ".join(result.errors))
