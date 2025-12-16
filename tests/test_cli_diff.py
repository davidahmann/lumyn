import json

import pytest
from typer.testing import CliRunner

from lumyn.cli.main import app

runner = CliRunner()


@pytest.fixture
def diff_workspace(tmp_path):
    # 1. Create a dummy dataset (past records)
    records = [
        {
            "schema_version": "decision_record.v1",
            "decision_id": "rec_001",
            "verdict": "ALLOW",
            "reason_codes": ["LEGACY_TRUST"],
            "request": {
                "schema_version": "decision_request.v1",
                "request_id": "req_001",
                "tenant": {"tenant_id": "t1"},
                "subject": {"type": "user", "id": "u1"},
                "action": {
                    "type": "support.refund",
                    "intent": "test",
                    "amount": {"value": 10, "currency": "USD"},
                },
                "evidence": {"risk": "low"},
                "context": {
                    "mode": "digest_only",
                    "digest": "sha256:"
                    + "0000000000000000000000000000000000000000000000000000000000000000",
                },
            },
        },
        {
            "schema_version": "decision_record.v1",
            "decision_id": "rec_002",
            "verdict": "DENY",
            "reason_codes": ["HIGH_RISK"],
            "request": {
                "schema_version": "decision_request.v1",
                "request_id": "req_002",
                "tenant": {"tenant_id": "t1"},
                "subject": {"type": "user", "id": "u2"},
                "action": {
                    "type": "support.refund",
                    "intent": "test",
                    "amount": {"value": 1000, "currency": "USD"},
                },
                "evidence": {"risk": "high"},
                "context": {
                    "mode": "digest_only",
                    "digest": "sha256:"
                    + "1111111111111111111111111111111111111111111111111111111111111111",
                },
            },
        },
    ]

    dataset_path = tmp_path / "past_traffic.json"
    dataset_path.write_text(json.dumps(records), encoding="utf-8")

    # 2. Create a "Strict" Policy that allows NOTHING (reverts ALLOW -> DENY)
    policy_path = tmp_path / "strict.v1.yml"
    policy_path.write_text(
        """
schema_version: policy.v1
policy_id: strict-test
policy_version: "1.0.0"
defaults:
  mode: enforce
  default_verdict: DENY
  default_reason_code: STRICT_DEFAULT
rules:
  - id: DUMMY
    stage: HARD_BLOCKS
    if: { evidence.dummy_is: never_match }
    then: { verdict: DENY, reason_codes: [DUMMY_RC] }
""",
        encoding="utf-8",
    )

    # 3. Create a "Loose" Policy that matches history
    policy_loose_path = tmp_path / "loose.v1.yml"
    policy_loose_path.write_text(
        """
schema_version: policy.v1
policy_id: loose-test
policy_version: "1.0.0"
defaults:
  mode: enforce
  default_verdict: ALLOW
  default_reason_code: DEFAULT_ALLOW
rules:
  - id: R1
    stage: HARD_BLOCKS
    if: { evidence.risk_is: high }
    then: { verdict: DENY, reason_codes: [HIGH_RISK] }
""",
        encoding="utf-8",
    )

    return dataset_path, policy_path, policy_loose_path


def test_diff_regressions(diff_workspace) -> None:
    dataset, strict_policy, _ = diff_workspace

    # Run diff with strict policy -> Should find regressions
    result = runner.invoke(app, ["diff", str(dataset), "--policy", str(strict_policy)])

    assert result.exit_code == 1, (
        f"Expected 1 (Regressions), got {result.exit_code}. "
        f"Stdout: {result.stdout} Stderr: {result.stderr}"
    )
    assert "Changes: 1" in result.stdout
    assert "rec_001" in result.stdout
    assert "ALLOW" in result.stdout
    assert "DENY" in result.stdout
    assert "rec_002" not in result.stdout  # Should be same (DENY -> DENY)


def test_diff_clean(diff_workspace) -> None:
    dataset, _, loose_policy = diff_workspace

    # Run diff with loose policy -> Should match
    # (rec_001 ALLOW->ALLOW via default, rec_002 DENY->DENY via rule)
    result = runner.invoke(app, ["diff", str(dataset), "--policy", str(loose_policy)])

    assert result.exit_code == 0, (
        f"Expected 0 (Clean), got {result.exit_code}. "
        f"Stdout: {result.stdout} Stderr: {result.stderr}"
    )
    assert "No regressions found" in result.stdout
