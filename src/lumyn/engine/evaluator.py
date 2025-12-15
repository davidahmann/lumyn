from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lumyn.engine.normalize import NormalizedRequest, normalize_request

STAGES = ("REQUIREMENTS", "HARD_BLOCKS", "ESCALATIONS", "TRUST_PATHS")
VERDICT_PRECEDENCE = {"ABSTAIN": 3, "QUERY": 2, "ESCALATE": 1, "TRUST": 0}


@dataclass(frozen=True, slots=True)
class MatchedRule:
    rule_id: str
    stage: str
    effect: str
    reason_codes: list[str]


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    verdict: str
    reason_codes: list[str]
    matched_rules: list[MatchedRule]
    queries: list[dict[str, str]]
    obligations: list[dict[str, Any]]


def _when_matches(action_type: str, when: dict[str, Any] | None) -> bool:
    if not when:
        return True
    if "action_type" in when:
        value = when["action_type"]
        return isinstance(value, str) and value == action_type
    if "action_type_in" in when:
        values = when["action_type_in"]
        if not isinstance(values, list):
            return False
        allowed = [v for v in values if isinstance(v, str)]
        return action_type in allowed
    return False


def _value_from_key(key: str, normalized: NormalizedRequest) -> Any:
    if key == "amount_currency":
        return normalized.amount_currency
    if key == "amount_usd":
        return normalized.amount_usd
    if key == "evidence.fx_rate_to_usd_present":
        return normalized.fx_rate_to_usd_present
    if key.startswith("evidence."):
        return normalized.evidence.get(key.removeprefix("evidence."))
    raise KeyError(key)


def _eval_condition(key: str, expected: Any, normalized: NormalizedRequest) -> bool:
    if key == "amount_currency_is":
        return bool(_value_from_key("amount_currency", normalized) == expected)
    if key == "amount_currency_ne":
        return bool(_value_from_key("amount_currency", normalized) != expected)

    if key == "amount_usd_gt":
        val = _value_from_key("amount_usd", normalized)
        return isinstance(val, int | float) and val > float(expected)
    if key == "amount_usd_gte":
        val = _value_from_key("amount_usd", normalized)
        return isinstance(val, int | float) and val >= float(expected)
    if key == "amount_usd_lt":
        val = _value_from_key("amount_usd", normalized)
        return isinstance(val, int | float) and val < float(expected)
    if key == "amount_usd_lte":
        val = _value_from_key("amount_usd", normalized)
        return isinstance(val, int | float) and val <= float(expected)

    if key == "evidence.fx_rate_to_usd_present":
        if not isinstance(expected, bool):
            return False
        return bool(_value_from_key(key, normalized)) is expected

    if key == "evidence.payment_instrument_risk_is":
        return bool(_value_from_key("evidence.payment_instrument_risk", normalized) == expected)
    if key == "evidence.payment_instrument_risk_in":
        val = _value_from_key("evidence.payment_instrument_risk", normalized)
        if not isinstance(expected, list):
            return False
        allowed = [v for v in expected if isinstance(v, str)]
        return val in allowed

    if key == "evidence.failure_similarity_score_gte":
        val = _value_from_key("evidence.failure_similarity_score", normalized)
        return isinstance(val, int | float) and val >= float(expected)

    if key == "evidence.chargeback_risk_gte":
        val = _value_from_key("evidence.chargeback_risk", normalized)
        return isinstance(val, int | float) and val >= float(expected)
    if key == "evidence.chargeback_risk_lt":
        val = _value_from_key("evidence.chargeback_risk", normalized)
        return isinstance(val, int | float) and val < float(expected)

    if key == "evidence.previous_refund_count_90d_gte":
        val = _value_from_key("evidence.previous_refund_count_90d", normalized)
        return isinstance(val, int) and val >= int(expected)
    if key == "evidence.previous_refund_count_90d_lt":
        val = _value_from_key("evidence.previous_refund_count_90d", normalized)
        return isinstance(val, int) and val < int(expected)

    if key == "evidence.customer_age_days_lt":
        val = _value_from_key("evidence.customer_age_days", normalized)
        return isinstance(val, int) and val < int(expected)
    if key == "evidence.customer_age_days_gte":
        val = _value_from_key("evidence.customer_age_days", normalized)
        return isinstance(val, int) and val >= int(expected)

    if key == "evidence.account_takeover_risk_gte":
        val = _value_from_key("evidence.account_takeover_risk", normalized)
        return isinstance(val, int | float) and val >= float(expected)

    if key == "evidence.manual_approval_is":
        val = _value_from_key("evidence.manual_approval", normalized)
        return isinstance(val, bool) and isinstance(expected, bool) and val is expected

    raise ValueError(f"unsupported condition key: {key}")


def _expr_matches(expr: dict[str, Any] | None, normalized: NormalizedRequest) -> bool:
    if not expr:
        return True
    return all(_eval_condition(key, expected, normalized) for key, expected in expr.items())


def _required_evidence_missing(
    *,
    action_type: str,
    normalized: NormalizedRequest,
    required_evidence: dict[str, Any],
) -> bool:
    required = required_evidence.get(action_type)
    if not isinstance(required, list):
        return False
    for key in required:
        if not isinstance(key, str):
            continue
        if key not in normalized.evidence or normalized.evidence.get(key) in (None, ""):
            return True
    return False


def evaluate_policy(
    request: dict[str, Any],
    *,
    policy: dict[str, Any],
) -> EvaluationResult:
    normalized = normalize_request(request)
    action_type = normalized.action_type

    matched_rules: list[MatchedRule] = []
    reason_codes: list[str] = []
    queries: list[dict[str, str]] = []
    obligations: list[dict[str, Any]] = []

    required_evidence = policy.get("required_evidence")
    required_evidence_map: dict[str, Any] = (
        dict(required_evidence) if isinstance(required_evidence, dict) else {}
    )

    rules = policy.get("rules", [])
    rules_list = rules if isinstance(rules, list) else []

    for stage in STAGES:
        for rule in rules_list:
            if not isinstance(rule, dict):
                continue
            if rule.get("stage") != stage:
                continue
            rule_id = str(rule.get("id"))

            when = rule.get("when")
            if not _when_matches(action_type, when if isinstance(when, dict) else None):
                continue

            if stage == "REQUIREMENTS" and not any(
                rule.get(k) is not None for k in ("if", "if_all", "if_any")
            ):
                if not _required_evidence_missing(
                    action_type=action_type,
                    normalized=normalized,
                    required_evidence=required_evidence_map,
                ):
                    continue

            expr_if = rule.get("if")
            if expr_if is not None and not _expr_matches(
                expr_if if isinstance(expr_if, dict) else None, normalized
            ):
                continue

            expr_if_all = rule.get("if_all")
            if expr_if_all is not None:
                if not isinstance(expr_if_all, list):
                    continue
                if not all(
                    _expr_matches(expr if isinstance(expr, dict) else None, normalized)
                    for expr in expr_if_all
                ):
                    continue

            expr_if_any = rule.get("if_any")
            if expr_if_any is not None:
                if not isinstance(expr_if_any, list):
                    continue
                if not any(
                    _expr_matches(expr if isinstance(expr, dict) else None, normalized)
                    for expr in expr_if_any
                ):
                    continue

            then = rule.get("then", {})
            if not isinstance(then, dict):
                continue
            effect = then.get("verdict")
            if effect not in VERDICT_PRECEDENCE:
                continue
            then_reason_codes = then.get("reason_codes", [])
            if not isinstance(then_reason_codes, list) or not all(
                isinstance(code, str) for code in then_reason_codes
            ):
                continue

            matched_rules.append(
                MatchedRule(
                    rule_id=rule_id,
                    stage=stage,
                    effect=effect,
                    reason_codes=list(then_reason_codes),
                )
            )
            reason_codes.extend(then_reason_codes)

            then_queries = then.get("queries", [])
            if isinstance(then_queries, list):
                for item in then_queries:
                    if (
                        isinstance(item, dict)
                        and isinstance(item.get("field"), str)
                        and isinstance(item.get("question"), str)
                    ):
                        queries.append({"field": item["field"], "question": item["question"]})

            then_obligations = then.get("obligations", [])
            if isinstance(then_obligations, list):
                for item in then_obligations:
                    if not isinstance(item, dict):
                        continue
                    obligation = dict(item)
                    obligation.setdefault("source", {})
                    source = obligation.get("source")
                    if isinstance(source, dict):
                        source.setdefault("rule_id", rule_id)
                        source.setdefault("stage", stage)
                    else:
                        obligation["source"] = {"rule_id": rule_id, "stage": stage}
                    obligations.append(obligation)

    if not matched_rules:
        defaults_raw = policy.get("defaults")
        defaults: dict[str, Any] = defaults_raw if isinstance(defaults_raw, dict) else {}
        default_verdict = defaults.get("default_verdict", "ESCALATE")
        default_reason = defaults.get("default_reason_code", "NO_MATCH_DEFAULT_ESCALATE")
        matched_rules.append(
            MatchedRule(
                rule_id="DEFAULT",
                stage="DEFAULT",
                effect=default_verdict,
                reason_codes=[default_reason],
            )
        )
        reason_codes.append(default_reason)

    final_verdict = max(matched_rules, key=lambda r: VERDICT_PRECEDENCE.get(r.effect, -1)).effect

    if final_verdict != "QUERY":
        queries = []

    return EvaluationResult(
        verdict=final_verdict,
        reason_codes=reason_codes,
        matched_rules=matched_rules,
        queries=queries,
        obligations=obligations,
    )
