from __future__ import annotations

from typing import Any

from lumyn.engine.normalize_v1 import NormalizedRequestV1, normalize_request_v1
from lumyn.records.emit_v1 import EvaluationResultV1, MatchedRuleV1

# v1 Stages - matched against policy.v1 spec
STAGES = ("REQUIREMENTS", "HARD_BLOCKS", "ESCALATIONS", "ALLOW_PATHS")

# v1 Verdict Precedence
# ABSTAIN (System/Input failure) > DENY > ESCALATE > ALLOW
VERDICT_PRECEDENCE_V1 = {"ABSTAIN": 3, "DENY": 2, "ESCALATE": 1, "ALLOW": 0}

# Supported Condition Keys (v1 strict)
SUPPORTED_KEYS = {
    "action_type",
    "amount_currency",
    "amount_currency_ne",
    "amount_usd",
    "amount_usd_gt",
    "amount_usd_gte",
    "amount_usd_lt",
    "amount_usd_lte",
}


def _value_from_key(key: str, normalized: NormalizedRequestV1) -> Any:
    # Similar to v0 but typed for NormalizedRequestV1
    if key == "amount_currency":
        return normalized.amount_currency
    if key == "amount_usd":
        return normalized.amount_usd
    if key == "evidence.fx_rate_to_usd_present":
        return normalized.fx_rate_to_usd_present
    if key.startswith("evidence."):
        # Extract actual evidence key by removing "evidence." prefix AND operator suffix
        # allowed suffixes: _is, _in, _gt, _gte, _lt, _lte
        # e.g. "evidence.risk_score_gt" -> "risk_score"

        inner = key.removeprefix("evidence.")
        # Optimization: try to strictly remove known suffixes
        for suffix in ("_is", "_ne", "_in", "_gt", "_gte", "_lt", "_lte"):
            if inner.endswith(suffix):
                evidence_key = inner.removesuffix(suffix)
                return normalized.evidence.get(evidence_key)

        # Fallback if no suffix matched (should verify if this is allowed)?
        # For now, return raw evidence key lookup if someone uses raw key.
        # (This is invalid in V1 spec but safe here to return None)
        return normalized.evidence.get(inner)

    raise KeyError(key)


def _eval_condition(key: str, expected: Any, normalized: NormalizedRequestV1) -> bool:
    # Reusing logic but targeting NormalizedRequestV1
    # Basic operators
    if key == "amount_currency_is":
        return bool(_value_from_key("amount_currency", normalized) == expected)
    if key == "amount_currency_ne":
        return bool(_value_from_key("amount_currency", normalized) != expected)

    if key == "amount_usd_gt":
        val = _value_from_key("amount_usd", normalized)
        return isinstance(val, (int, float)) and val > float(expected)
    if key == "amount_usd_gte":
        val = _value_from_key("amount_usd", normalized)
        return isinstance(val, (int, float)) and val >= float(expected)
    if key == "amount_usd_lt":
        val = _value_from_key("amount_usd", normalized)
        return isinstance(val, (int, float)) and val < float(expected)
    if key == "amount_usd_lte":
        val = _value_from_key("amount_usd", normalized)
        return isinstance(val, (int, float)) and val <= float(expected)

    if key.endswith("evidence.fx_rate_to_usd_present"):
        # Special case from v0, useful to keep?
        # Let's support it via strict key check if we want, or rely on _is: null check.
        pass

    if key == "amount_currency_ne":
        return bool(_value_from_key("amount_currency", normalized) != expected)

    # Generic evidence matching
    if key.startswith("evidence."):
        # Simplified generic checking for v1 basic keys
        suffix = key.split("_")[-1]
        valid_suffixes = {"is", "ne", "in", "gt", "gte", "lt", "lte"}

        # Check if suffix is a valid operator, else assume the key implies existence?
        # V1 spec says keys MUST be `evidence.<key>_is`, `_in`, etc.
        # We need to extract the base evidence key.

        if suffix in valid_suffixes:
            # Reconstruct evidence key (everything before the suffix)
            # e.g. evidence.risk_score_gt -> evidence.risk_score
            # But wait, what if key has underscores?
            # evidence.user_age_is -> user_age
            # We should use rsplit or strict parsing.
            pass
        else:
            # If key doesn't end with operator output false (invalid key)
            return False

        val = _value_from_key(key, normalized)
        if key.endswith("_is"):
            return bool(val == expected)
        if key.endswith("_ne"):
            return bool(val != expected)
        if key.endswith("_in") and isinstance(expected, list):
            return val in expected
        if key.endswith("_gte") and isinstance(val, (int, float)):
            return val >= float(expected)
        if key.endswith("_gt") and isinstance(val, (int, float)):
            return val > float(expected)
        if key.endswith("_lte") and isinstance(val, (int, float)):
            return val <= float(expected)
        if key.endswith("_lt") and isinstance(val, (int, float)):
            return val < float(expected)

    return False


def _expr_matches(expr: dict[str, Any] | None, normalized: NormalizedRequestV1) -> bool:
    if not expr:
        return True
    try:
        return all(_eval_condition(key, expected, normalized) for key, expected in expr.items())
    except KeyError:
        return False  # Fail safe on unknown keys? Or strictly error?
        # For v1 engine, lets return False for non-matching keys to avoid crashes.
        # We enforce validation in `validate.py`.


def evaluate_policy_v1(
    request: dict[str, Any],
    *,
    policy: dict[str, Any],
) -> EvaluationResultV1:
    normalized = normalize_request_v1(request)
    action_type = normalized.action_type

    matched_rules: list[MatchedRuleV1] = []
    reason_codes: list[str] = []
    queries: list[dict[str, str]] = []
    obligations: list[dict[str, Any]] = []

    # v1 policy logic ...
    # This logic mimics the v0 loop but uses v1 dataclasses/verdicts

    rules = policy.get("rules", [])
    rules_list = rules if isinstance(rules, list) else []

    for stage in STAGES:
        for rule in rules_list:
            if not isinstance(rule, dict):
                continue
            if rule.get("stage") != stage:
                continue
            rule_id = str(rule.get("id"))

            when = rule.get("when", {})
            # Simplified match
            if when and when.get("action_type") and when["action_type"] != action_type:
                continue

            # Check if/if_all/if_any

            # 1. "if": match ALL conditions in the dict (implicit AND)
            expr_if = rule.get("if")
            if expr_if and not _expr_matches(expr_if, normalized):
                continue

            # 2. "if_all": list of condition dicts, ALL must match
            expr_if_all = rule.get("if_all")
            if expr_if_all:
                if not all(_expr_matches(cond, normalized) for cond in expr_if_all):
                    continue

            # 3. "if_any": list of condition dicts, AT LEAST ONE must match
            expr_if_any = rule.get("if_any")
            if expr_if_any:
                if not any(_expr_matches(cond, normalized) for cond in expr_if_any):
                    continue

            then = rule.get("then", {})
            effect = then.get("verdict")
            if effect not in VERDICT_PRECEDENCE_V1:
                # Mapper from v0 terms if we are using v0 policies in v1 engine?
                # TRUST -> ALLOW, QUERY -> DENY
                if effect == "TRUST":
                    effect = "ALLOW"
                elif effect == "QUERY":
                    effect = "DENY"
                elif effect not in VERDICT_PRECEDENCE_V1:
                    continue

            then_reason_codes = then.get("reason_codes", [])

            matched_rules.append(
                MatchedRuleV1(
                    rule_id=rule_id,
                    stage=stage,
                    effect=effect,
                    reason_codes=list(then_reason_codes),
                )
            )
            reason_codes.extend(then_reason_codes)

            # Queries (on DENY)
            if effect == "DENY":
                then_queries = then.get("queries", [])
                for q in then_queries:
                    queries.append(q)

            # Obligations (on ALLOW/DENY?)
            for o in then.get("obligations", []):
                obligations.append(o)

    # Defaults
    if not matched_rules:
        defaults = policy.get("defaults", {})
        default_verdict = defaults.get("default_verdict", "ESCALATE")
        if default_verdict == "TRUST":
            default_verdict = "ALLOW"
        if default_verdict == "QUERY":
            default_verdict = "DENY"

        default_reason = defaults.get("default_reason_code", "NO_MATCH_DEFAULT_ESCALATE")

        matched_rules.append(
            MatchedRuleV1(
                rule_id="DEFAULT",
                stage="DEFAULT",
                effect=default_verdict,
                reason_codes=[default_reason],
            )
        )
        reason_codes.append(default_reason)

    final_verdict = max(matched_rules, key=lambda r: VERDICT_PRECEDENCE_V1.get(r.effect, -1)).effect

    if final_verdict != "DENY":
        queries = []  # Only return queries if DENY? Or if verdict requires info? V0 is QUERY only.

    return EvaluationResultV1(
        verdict=final_verdict,
        reason_codes=reason_codes,
        matched_rules=matched_rules,
        queries=queries,
        obligations=obligations,
    )
