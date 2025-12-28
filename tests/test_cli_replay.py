from __future__ import annotations

import json
import zipfile
from pathlib import Path

import yaml
from typer.testing import CliRunner

from lumyn.cli.main import app
from lumyn.engine.normalize_v1 import (
    build_memory_snapshot_v1,
    compute_inputs_digest_v1,
    normalize_request_v1,
)
from lumyn.policy.loader import compute_policy_hash


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


def test_cli_replay_rejects_tampered_memory_snapshot_digest(tmp_path: Path) -> None:
    runner = CliRunner()

    request = {
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
        "context": {"mode": "digest_only", "digest": "sha256:" + ("a" * 64)},
    }

    policy_obj = {
        "schema_version": "policy.v1",
        "policy_id": "test-policy",
        "policy_version": "1.0.0",
        "defaults": {
            "mode": "enforce",
            "default_verdict": "ESCALATE",
            "default_reason_code": "NO_MATCH_DEFAULT_ESCALATE",
        },
        "rules": [
            {
                "id": "R1",
                "stage": "ALLOW_PATHS",
                "when": {"action_type": "support.refund"},
                "if": {"amount_usd_lte": 25},
                "then": {"verdict": "ALLOW", "reason_codes": ["REFUND_SMALL_LOW_RISK"]},
            }
        ],
    }

    policy_text = yaml.safe_dump(policy_obj, sort_keys=True)
    policy_hash = compute_policy_hash(policy_obj)

    normalized = normalize_request_v1(request)
    inputs_digest = compute_inputs_digest_v1(request, normalized=normalized)

    memory_snapshot = build_memory_snapshot_v1(
        projection_model="stub/projection",
        query_top_k=5,
        risk_threshold=0.9,
        success_allow_threshold=0.98,
        hits=[{"decision_id": "dec_123", "outcome": -1, "score": 0.95}],
    )

    record = {
        "schema_version": "decision_record.v1",
        "decision_id": "01JZ1S7Y1NQ2A0D5JQK2Q2P3X4",
        "created_at": "2025-12-15T10:00:00Z",
        "trace": {},
        "request": request,
        "policy": {
            "policy_id": "test-policy",
            "policy_version": "1.0.0",
            "policy_hash": policy_hash,
            "mode": "enforce",
        },
        "verdict": "ALLOW",
        "reason_codes": ["REFUND_SMALL_LOW_RISK"],
        "matched_rules": [{"rule_id": "R1", "stage": "ALLOW_PATHS", "effect": "ALLOW"}],
        "risk_signals": {},
        "queries": [],
        "obligations": [],
        "determinism": {
            "engine_version": "test",
            "evaluation_order": [
                "REQUIREMENTS",
                "HARD_BLOCKS",
                "ESCALATIONS",
                "ALLOW_PATHS",
                "DEFAULT",
            ],
            "inputs_digest": inputs_digest,
            "memory": memory_snapshot,
        },
        "extensions": {},
    }

    pack_path = tmp_path / "pack.zip"
    with zipfile.ZipFile(pack_path, "w") as zf:
        zf.writestr("decision_record.json", json.dumps(record, sort_keys=True))
        zf.writestr("request.json", json.dumps(request, sort_keys=True))
        zf.writestr("policy.yml", policy_text)

    ok = runner.invoke(app, ["replay", str(pack_path)])
    assert ok.exit_code == 0, ok.stdout

    record_tampered = dict(record)
    record_tampered["determinism"] = dict(record["determinism"])
    record_tampered["determinism"]["memory"] = dict(memory_snapshot)
    record_tampered["determinism"]["memory"]["snapshot_digest"] = "sha256:" + ("0" * 64)

    tampered_path = tmp_path / "pack_tampered.zip"
    with zipfile.ZipFile(tampered_path, "w") as zf:
        zf.writestr("decision_record.json", json.dumps(record_tampered, sort_keys=True))
        zf.writestr("request.json", json.dumps(request, sort_keys=True))
        zf.writestr("policy.yml", policy_text)

    bad = runner.invoke(app, ["replay", str(tampered_path)])
    assert bad.exit_code == 1
    combined = (bad.stdout or "") + getattr(bad, "stderr", "")
    combined = combined or getattr(bad, "output", "")
    assert "memory_snapshot digest mismatch" in combined
