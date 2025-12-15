from __future__ import annotations

import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app


def test_cli_export_pack_zip_contains_policy_snapshot(tmp_path: Path) -> None:
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
                    "intent": "Refund duplicate charge for order 82731",
                    "amount": {"value": 42.5, "currency": "USD"},
                },
                "context": {
                    "mode": "digest_only",
                    "digest": (
                        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                    ),
                },
            },
            separators=(",", ":"),
            sort_keys=True,
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

    out_zip = tmp_path / "pack.zip"
    exported = runner.invoke(
        app,
        [
            "export",
            record["decision_id"],
            "--workspace",
            str(workspace),
            "--out",
            str(out_zip),
            "--pack",
        ],
    )
    assert exported.exit_code == 0
    assert out_zip.exists()

    with zipfile.ZipFile(out_zip) as zf:
        names = set(zf.namelist())
        assert "decision_record.json" in names
        assert "policy.yml" in names
        assert "request.json" in names
        assert "README.txt" in names
        policy_text = zf.read("policy.yml").decode("utf-8")
        assert "policy_id:" in policy_text
