from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from lumyn.policy.errors import PolicyError
from lumyn.policy.loader import compute_policy_hash, load_policy
from lumyn.policy.validate import validate_policy_or_raise


def test_policy_load_and_hash() -> None:
    loaded = load_policy("policies/lumyn-support.v0.yml")
    assert loaded.policy_hash.startswith("sha256:")
    assert len(loaded.policy_hash) == len("sha256:") + 64


def test_policy_hash_is_stable_against_whitespace_changes() -> None:
    policy_path = Path("policies/lumyn-support.v0.yml")
    original = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    original_hash = compute_policy_hash(original)

    mutated_text = "\n\n" + textwrap.dedent(policy_path.read_text(encoding="utf-8")) + "\n\n"
    mutated = yaml.safe_load(mutated_text)
    mutated_hash = compute_policy_hash(mutated)

    assert original_hash == mutated_hash


def test_policy_validation_rejects_unknown_reason_code() -> None:
    policy = yaml.safe_load(Path("policies/lumyn-support.v0.yml").read_text(encoding="utf-8"))
    assert isinstance(policy, dict)
    policy["defaults"]["default_reason_code"] = "NOT_A_REAL_REASON"
    with pytest.raises(PolicyError):
        validate_policy_or_raise(
            policy,
            policy_schema_path=Path("schemas/policy.v0.schema.json"),
            reason_codes_path=Path("schemas/reason_codes.v0.json"),
        )
