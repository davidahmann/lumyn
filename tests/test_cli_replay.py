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

    decided = runner.invoke(
        app,
        ["decide", "--workspace", str(workspace), "--in", str(request_path)],
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
