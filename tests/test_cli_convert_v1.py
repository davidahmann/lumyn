from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app


def test_cli_convert_record_v0_to_v1(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": "decision_request.v0",
                "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
                "action": {"type": "support.update_ticket", "intent": "Update ticket"},
                "context": {"mode": "digest_only", "digest": "sha256:" + ("b" * 64)},
            }
        ),
        encoding="utf-8",
    )

    # Explicitly init v0 policy for legacy test
    runner.invoke(
        app,
        [
            "init",
            "--workspace",
            str(workspace),
            "--policy-template",
            "policies/lumyn-support.v0.yml",
        ],
    )

    decided = runner.invoke(
        app,
        ["decide", "--workspace", str(workspace), str(request_path)],
    )
    assert decided.exit_code == 0
    record = json.loads(decided.stdout)

    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")

    converted = runner.invoke(app, ["convert", str(record_path), "--to", "v1"])
    assert converted.exit_code == 0
    out = json.loads(converted.stdout)
    assert out["schema_version"] == "decision_record.v1"
    assert out["verdict"] in {"ALLOW", "DENY", "ABSTAIN", "ESCALATE"}
    assert out["request"]["schema_version"] == "decision_request.v1"


def test_cli_convert_query_maps_to_deny(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": "decision_request.v0",
                "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
                "action": {
                    "type": "support.refund",
                    "intent": "Refund (missing evidence => QUERY)",
                    "amount": {"value": 12.0, "currency": "USD"},
                },
                "evidence": {},
                "context": {"mode": "digest_only", "digest": "sha256:" + ("b" * 64)},
            }
        ),
        encoding="utf-8",
    )

    # Explicitly init v0 policy for legacy test
    runner.invoke(
        app,
        [
            "init",
            "--workspace",
            str(workspace),
            "--policy-template",
            "policies/lumyn-support.v0.yml",
        ],
    )

    decided = runner.invoke(
        app,
        ["decide", "--workspace", str(workspace), str(request_path)],
    )
    assert decided.exit_code == 0
    record_v0 = json.loads(decided.stdout)
    assert record_v0["verdict"] == "QUERY"

    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(record_v0), encoding="utf-8")

    converted = runner.invoke(app, ["convert", str(record_path), "--to", "v1"])
    assert converted.exit_code == 0
    record_v1 = json.loads(converted.stdout)
    assert record_v1["verdict"] == "DENY"
