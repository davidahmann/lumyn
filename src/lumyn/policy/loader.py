from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from lumyn.assets import read_builtin_text
from lumyn.policy.spec import LoadedPolicy
from lumyn.policy.validate import validate_policy_or_raise


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def compute_policy_hash(policy: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json_bytes(policy)).hexdigest()
    return f"sha256:{digest}"


def read_policy_text(path: str | Path) -> str:
    policy_path = Path(path)
    if policy_path.exists():
        return policy_path.read_text(encoding="utf-8")
    return read_builtin_text(str(policy_path).lstrip("./"))


def load_policy(
    path: str | Path,
    *,
    policy_schema_path: str | Path = "schemas/policy.v0.schema.json",
    reason_codes_path: str | Path = "schemas/reason_codes.v0.json",
) -> LoadedPolicy:
    policy_text = read_policy_text(path)
    policy = yaml.safe_load(policy_text)
    if not isinstance(policy, Mapping):
        raise ValueError(f"policy file did not parse to an object: {path}")

    schema_version = policy.get("schema_version", "policy.v0")
    if schema_version.startswith("policy.v1"):
        # Use v1 schema
        # If user passed default v0 schema, swap it. If they passed custom, respect it?
        # Actually load_policy defaults are strict v0 paths.
        if str(policy_schema_path).endswith("policy.v0.schema.json"):
            policy_schema_path = "schemas/policy.v1.schema.json"

        validate_policy_or_raise(
            policy,
            policy_schema_path=policy_schema_path,
            reason_codes_path=None,  # v1 does not use strict reason code list yet
        )
    else:
        validate_policy_or_raise(
            policy,
            policy_schema_path=policy_schema_path,
            reason_codes_path=reason_codes_path,
        )

    return LoadedPolicy(policy=policy, policy_hash=compute_policy_hash(policy))
