from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app


def test_markdown_ticket_summary_is_capped(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    obligations = "\n".join(
        [
            "        - type: check",
            '          title: "Confirm action preconditions"',
            '          details: "Ensure required systems are reachable and inputs are validated."',
        ]
        * 80
    )
    policy_text = "\n".join(
        [
            "schema_version: policy.v0",
            "policy_id: test-policy",
            'policy_version: "0.1.0"',
            "",
            "defaults:",
            "  mode: enforce",
            "  default_verdict: ESCALATE",
            "  default_reason_code: NO_MATCH_DEFAULT_ESCALATE",
            "",
            "required_evidence:",
            "  support.update_ticket: [ticket_id]",
            "",
            "rules:",
            "  - id: R1",
            "    stage: TRUST_PATHS",
            "    when: { action_type: support.update_ticket }",
            "    then:",
            "      verdict: TRUST",
            "      reason_codes: [UPDATE_TICKET_OK]",
            "      obligations:",
            obligations,
            "",
        ]
    )
    policy_template = tmp_path / "policy.yml"
    policy_template.write_text(policy_text, encoding="utf-8")

    init = runner.invoke(
        app,
        [
            "init",
            "--workspace",
            str(workspace),
            "--policy-template",
            str(policy_template),
            "--force",
        ],
    )
    assert init.exit_code == 0, init.stdout

    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": "decision_request.v0",
                "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
                "action": {"type": "support.update_ticket", "intent": "Update ticket"},
                "evidence": {"ticket_id": "ZD-4002"},
                "context": {"mode": "digest_only", "digest": "sha256:" + ("b" * 64)},
            }
        ),
        encoding="utf-8",
    )

    decided = runner.invoke(
        app,
        ["decide", "--workspace", str(workspace), str(request_path)],
    )
    assert decided.exit_code == 0, decided.stdout
    record = json.loads(decided.stdout)

    explained = runner.invoke(
        app,
        [
            "explain",
            record["decision_id"],
            "--workspace",
            str(workspace),
            "--markdown",
        ],
    )
    assert explained.exit_code == 0, explained.stdout
    lines = explained.stdout.strip("\n").splitlines()

    assert len(lines) <= 40
    assert any("truncated" in line for line in lines)
