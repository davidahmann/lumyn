from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app
from lumyn.store.sqlite import SqliteStore


def test_cli_init_creates_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"
    result = runner.invoke(app, ["init", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert (workspace / "policy.yml").exists()
    assert (workspace / "lumyn.db").exists()


def test_cli_init_works_without_repo_assets() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        workspace = Path(".lumyn").resolve()
        result = runner.invoke(app, ["init", "--workspace", str(workspace)])
        assert result.exit_code == 0
        assert (workspace / "policy.yml").exists()
        assert (workspace / "lumyn.db").exists()


def test_cli_demo_emits_multiple_records(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".lumyn"
    result = runner.invoke(app, ["demo", "--workspace", str(workspace)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert len(payload) >= 2
    assert all(isinstance(r, dict) for r in payload)


def test_cli_decide_show_and_label_updates_memory(tmp_path: Path) -> None:
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
                    "tags": ["duplicate_charge"],
                },
                "evidence": {
                    "ticket_id": "ZD-1001",
                    "order_id": "82731",
                    "customer_id": "C-9",
                },
                "context": {
                    "mode": "digest_only",
                    "digest": (
                        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                    ),
                },
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
    assert record["schema_version"] == "decision_record.v0"
    decision_id = record["decision_id"]

    shown = runner.invoke(app, ["show", decision_id, "--workspace", str(workspace)])
    assert shown.exit_code == 0
    shown_record = json.loads(shown.stdout)
    assert shown_record["decision_id"] == decision_id

    labeled = runner.invoke(
        app,
        [
            "label",
            decision_id,
            "--workspace",
            str(workspace),
            "--label",
            "failure",
            "--summary",
            "Bad outcome in demo",
        ],
    )
    assert labeled.exit_code == 0

    store = SqliteStore(workspace / "lumyn.db")
    memory = store.list_memory_items(
        tenant_id="acme",
        action_type="support.refund",
        label="failure",
        limit=10,
    )
    assert len(memory) == 1
