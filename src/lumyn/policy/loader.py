from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from lumyn.policy.spec import LoadedPolicy
from lumyn.policy.validate import validate_policy_or_raise


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def compute_policy_hash(policy: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json_bytes(policy)).hexdigest()
    return f"sha256:{digest}"


def load_policy(
    path: str | Path,
    *,
    policy_schema_path: str | Path = "schemas/policy.v0.schema.json",
    reason_codes_path: str | Path = "schemas/reason_codes.v0.json",
) -> LoadedPolicy:
    policy_path = Path(path)
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(policy, Mapping):
        raise ValueError(f"policy file did not parse to an object: {policy_path}")

    validate_policy_or_raise(
        policy,
        policy_schema_path=Path(policy_schema_path),
        reason_codes_path=Path(reason_codes_path),
    )

    return LoadedPolicy(policy=policy, policy_hash=compute_policy_hash(policy))
