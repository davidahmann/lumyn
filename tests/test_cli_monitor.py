from unittest.mock import patch

from typer.testing import CliRunner

from lumyn.cli.main import app
from lumyn.store.sqlite import SqliteStore

runner = CliRunner()


def test_monitor_reads_existing(tmp_path) -> None:
    # Setup workspace
    ws = tmp_path / "ws"
    ws.mkdir()
    db_path = ws / "lumyn.db"
    store = SqliteStore(db_path)
    store.init()

    # Pre-seed decisions
    store.put_decision_record(
        {
            "schema_version": "decision_record.v1",
            "decision_id": "d1",
            "created_at": "2023-01-01T12:00:00Z",
            "verdict": "ALLOW",
            "request": {"subject": {"id": "u1"}, "action": {"type": "lvl1"}},
            "policy": {
                "policy_id": "p1",
                "policy_version": "1",
                "policy_hash": "h1",
                "mode": "enforce",
            },
            "reason_codes": [],
        }
    )
    store.put_decision_record(
        {
            "schema_version": "decision_record.v1",
            "decision_id": "d2",
            "created_at": "2023-01-01T12:01:00Z",
            "verdict": "DENY",
            "request": {"subject": {"id": "u2"}, "action": {"type": "lvl2"}},
            "policy": {
                "policy_id": "p1",
                "policy_version": "1",
                "policy_hash": "h1",
                "mode": "enforce",
            },
            "reason_codes": [],
        }
    )

    # Mock sleep to raise KeyboardInterrupt to exit the loop
    # side_effect=[None, KeyboardInterrupt]:
    #   1. startup sleep(0.5) -> returns None
    #   2. loop sleep(interval) -> raises KeyboardInterrupt
    with patch("time.sleep", side_effect=[None, KeyboardInterrupt]):
        result = runner.invoke(app, ["monitor", "--workspace", str(ws), "--limit", "10"])

    # CliRunner might return 130 (SIGINT) even if handled, or 0.
    assert result.exit_code in [0, 130]
    assert "Connecting to the Matrix" in result.stdout
    assert "ALLOW" in result.stdout
    assert "DENY" in result.stdout
    assert "u1" in result.stdout
    assert "u2" in result.stdout
    assert "lvl1" in result.stdout
    assert "lvl2" in result.stdout
    assert "Disconnected." in result.stdout
