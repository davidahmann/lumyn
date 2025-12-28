from pathlib import Path

import pytest

from lumyn.policy.errors import PolicyError
from lumyn.policy.loader import load_policy


def test_v1_policy_validation_rejects_unsupported_keys(tmp_path: Path) -> None:
    policy_text = """
schema_version: policy.v1
policy_id: test-invalid-keys
policy_version: "1.0.0"
defaults:
  mode: enforce
  default_verdict: ESCALATE
  default_reason_code: NO_MATCH_DEFAULT_ESCALATE
rules:
  - id: R1
    stage: REQUIREMENTS
    if:
      evidence.unsupported_key_raw: true
    then:
      verdict: DENY
      reason_codes: [MISSING_EVIDENCE_REFUND]
"""
    p_path = tmp_path / "policy.yml"
    p_path.write_text(policy_text)

    with pytest.raises(PolicyError) as exc:
        load_policy(p_path)

    assert "unsupported condition key: evidence.unsupported_key_raw" in str(exc.value)


def test_v1_policy_validation_accepts_valid_suffixes(tmp_path: Path) -> None:
    policy_text = """
schema_version: policy.v1
policy_id: test-valid-keys
policy_version: "1.0.0"
defaults:
  mode: enforce
  default_verdict: ESCALATE
  default_reason_code: NO_MATCH_DEFAULT_ESCALATE
rules:
  - id: R1
    stage: REQUIREMENTS
    if:
      evidence.score_gt: 50
    then:
      verdict: ALLOW
      reason_codes: [UPDATE_TICKET_OK]
"""
    p_path = tmp_path / "policy.yml"
    p_path.write_text(policy_text)

    # Should not raise
    load_policy(p_path)


def test_v1_policy_validation_rejects_unknown_reason_codes(tmp_path: Path) -> None:
    policy_text = """
schema_version: policy.v1
policy_id: test-unknown-reason
policy_version: "1.0.0"
defaults:
  mode: enforce
  default_verdict: ESCALATE
  default_reason_code: NO_MATCH_DEFAULT_ESCALATE
rules:
  - id: R1
    stage: REQUIREMENTS
    if:
      evidence.score_gt: 50
    then:
      verdict: ALLOW
      reason_codes: [THIS_CODE_DOES_NOT_EXIST]
"""
    p_path = tmp_path / "policy.yml"
    p_path.write_text(policy_text)

    with pytest.raises(PolicyError) as exc:
        load_policy(p_path)

    assert "unknown reason code: THIS_CODE_DOES_NOT_EXIST" in str(exc.value)
