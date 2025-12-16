from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# v0 -> v1 Verdict Map
VERDICT_MAP = {"TRUST": "ALLOW", "QUERY": "DENY", "ABSTAIN": "ABSTAIN", "ESCALATE": "ESCALATE"}

# v1 Supported Condition Keys (strict)
V1_SUPPORTED_KEYS = {
    "action_type",
    "amount_currency",
    "amount_currency_ne",
    "amount_usd",
    "amount_usd_gt",
    "amount_usd_gte",
    "amount_usd_lt",
    "amount_usd_lte",
    # Extensible via evidence.* suffixes
}


def migrate_policy_v0_to_v1(policy_v0: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings = []

    # 1. Top-level headers
    policy_v1 = {
        "schema_version": "policy.v1",
        "policy_id": policy_v0.get("policy_id", "unknown"),
        "policy_version": "1.0.0",  # Default for migrated policies.
    }

    # 2. Defaults
    defaults_v0 = policy_v0.get("defaults", {})
    defaults_v1 = {
        "mode": defaults_v0.get("mode", "enforce"),
        "default_verdict": VERDICT_MAP.get(
            defaults_v0.get("default_verdict", "ESCALATE"), "ESCALATE"
        ),
        "default_reason_code": defaults_v0.get("default_reason_code", "NO_MATCH_DEFAULT"),
    }
    policy_v1["defaults"] = defaults_v1

    # 3. Rules
    rules_v1 = []
    for rule in policy_v0.get("rules", []):
        rule_bs = {}
        rule_id = rule.get("id")
        rule_bs["id"] = rule_id

        # Stage (Required in v1, same names generally)
        rule_bs["stage"] = rule.get("stage")

        # When
        if "when" in rule:
            rule_bs["when"] = rule["when"]
            # Validate 'when' conditions
            for k in rule_bs["when"]:
                # Basic check, v1 'when' is limited?
                # Evaluator v1 supports action_type in 'when'.
                pass

        # If/If_all/If_any
        for cond_type in ["if", "if_all", "if_any"]:
            if cond_type in rule:
                val = rule[cond_type]
                rule_bs[cond_type] = val
                # Check for unsupported keys
                # Flatten to list of dicts for checking
                conds = []
                if cond_type == "if":
                    conds = [val]
                elif isinstance(val, list):
                    conds = val

                for c in conds:
                    for k in c.keys():
                        if k not in V1_SUPPORTED_KEYS:
                            # Check evidence suffix
                            if k.startswith("evidence."):
                                suffix = k.split("_")[-1]
                                if suffix in {"is", "ne", "in", "gt", "gte", "lt", "lte"}:
                                    continue  # Valid suffix

                            # Fallback: report warning
                            warnings.append(
                                f"Rule {rule_id}: Potential unsupported key '{k}'. "
                                "Verify v1 engine supports it."
                            )

        # Then
        then_v0 = rule.get("then", {})
        verdict_v0 = then_v0.get("verdict")
        verdict_v1 = VERDICT_MAP.get(verdict_v0, verdict_v0)

        then_v1 = {"verdict": verdict_v1, "reason_codes": then_v0.get("reason_codes", [])}

        # Queries (only for DENY/ESCALATE usually, but v0 had them for QUERY)
        if "queries" in then_v0:
            then_v1["queries"] = then_v0["queries"]

        # Obligations
        if "obligations" in then_v0:
            then_v1["obligations"] = then_v0["obligations"]

        rule_bs["then"] = then_v1
        rules_v1.append(rule_bs)

    policy_v1["rules"] = rules_v1

    return policy_v1, warnings


def main() -> None:
    import sys

    if len(sys.argv) < 2:
        print("Usage: python migrate_v1.py <policy.v0.yml>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    data = yaml.safe_load(input_path.read_text())
    v1_policy, warns = migrate_policy_v0_to_v1(data)

    output_path = input_path.with_suffix(".v1.yml")
    with open(output_path, "w") as f:
        yaml.dump(v1_policy, f, sort_keys=False)

    print(f"Migrated policy written to {output_path}")
    if warns:
        print("\nWarnings:")
        for w in warns:
            print(f"- {w}")


if __name__ == "__main__":
    main()
