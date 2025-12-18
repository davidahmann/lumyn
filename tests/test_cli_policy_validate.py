"""Test lumyn policy validate command."""

from pathlib import Path

import pytest
import typer

from lumyn.cli.commands.policy import validate


def test_policy_validate_success(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test policy validate with valid policy."""
    workspace = tmp_path / ".lumyn"
    workspace.mkdir()

    policy_content = """schema_version: policy.v1
policy_id: test-policy
policy_version: 1.0.0
defaults:
  mode: enforce
  default_verdict: ESCALATE
  default_reason_code: NO_MATCH_DEFAULT
rules:
  - id: R001
    stage: REQUIREMENTS
    if: { action_type: "test.action" }
    then:
      verdict: ALLOW
      reason_codes: [TEST_ALLOW]
"""
    (workspace / "policy.yml").write_text(policy_content)

    validate(workspace=workspace, path=None)

    captured = capsys.readouterr()
    assert "ok" in captured.out
    assert "test-policy" in captured.out


def test_policy_validate_with_explicit_path(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test policy validate with explicit path."""
    policy_content = """schema_version: policy.v1
policy_id: custom-policy
policy_version: 2.0.0
defaults:
  mode: enforce
  default_verdict: ESCALATE
  default_reason_code: NO_MATCH_DEFAULT
rules:
  - id: R001
    stage: REQUIREMENTS
    if: { action_type: "custom.action" }
    then:
      verdict: ALLOW
      reason_codes: [CUSTOM_ALLOW]
"""
    policy_path = tmp_path / "custom.yml"
    policy_path.write_text(policy_content)

    validate(workspace=Path(".lumyn"), path=policy_path)

    captured = capsys.readouterr()
    assert "custom-policy" in captured.out


def test_policy_validate_missing_file(tmp_path: Path) -> None:
    """Test policy validate with missing file."""
    workspace = tmp_path / ".lumyn"
    workspace.mkdir()

    with pytest.raises(typer.Exit) as exc_info:
        validate(workspace=workspace, path=None)

    assert exc_info.value.exit_code == 1
