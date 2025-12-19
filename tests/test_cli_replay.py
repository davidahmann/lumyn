from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app


def test_cli_replay_validates_export_pack(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": "decision_request.v0",
                "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
                "action": {"type": "support.update_ticket", "intent": "Update ticket"},
                "context": {
                    "mode": "digest_only",
                    "digest": (
                        "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
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

    with runner.isolated_filesystem():
        Path("pack.zip").write_bytes(out_zip.read_bytes())
        replayed = runner.invoke(app, ["replay", "pack.zip"])
        assert replayed.exit_code == 0, replayed.stdout

        converted = runner.invoke(
            app, ["convert", "pack.zip", "--to", "v1", "--out", "pack_v1.zip"]
        )
        assert converted.exit_code == 0, converted.stdout

        replayed_v1 = runner.invoke(app, ["replay", "pack_v1.zip"])
        assert replayed_v1.exit_code == 0, replayed_v1.stdout


def test_cli_replay_validates_v1_export_pack(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"

    request_path = tmp_path / "request_v1.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": "decision_request.v1",
                "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
                "action": {
                    "type": "support.refund",
                    "intent": "Refund duplicate charge for order 82731",
                    "amount": {"value": 12.0, "currency": "USD"},
                },
                "evidence": {
                    "ticket_id": "ZD-1001",
                    "order_id": "82731",
                    "customer_id": "C-9",
                    "payment_instrument_risk": "low",
                    "chargeback_risk": 0.05,
                    "previous_refund_count_90d": 0,
                    "customer_age_days": 180,
                },
                "context": {
                    "mode": "digest_only",
                    "digest": "sha256:" + ("a" * 64),
                },
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    # Default init is v1 now.
    runner.invoke(app, ["init", "--workspace", str(workspace)])

    decided = runner.invoke(
        app,
        ["decide", "--workspace", str(workspace), str(request_path)],
    )
    assert decided.exit_code == 0, decided.stdout
    record = json.loads(decided.stdout)
    assert record["schema_version"] == "decision_record.v1"

    out_zip = tmp_path / "pack_v1_native.zip"
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

    with runner.isolated_filesystem():
        Path("pack.zip").write_bytes(out_zip.read_bytes())
        replayed = runner.invoke(app, ["replay", "pack.zip"])
        assert replayed.exit_code == 0, replayed.stdout
