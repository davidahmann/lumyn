import json
import shutil
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from lumyn.cli.main import app
from lumyn.memory.client import MemoryStore

DB_PATH = Path(".lumyn/test_learn.db")
MEM_PATH = Path(".lumyn/test_memory_cli")


def setup_module() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    if MEM_PATH.exists():
        shutil.rmtree(MEM_PATH)

    # Setup dummy DB
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE decisions (decision_id TEXT PRIMARY KEY, record_json TEXT)")

    # Insert a dummy record
    record = {
        "decision_id": "dec_learn_01",
        "verdict": "ALLOW",
        "created_at": "2023-10-01T10:00:00Z",
        "request": {
            "action": {"type": "refund", "amount": {"value": 50, "currency": "USD"}},
            "evidence": {"risk": 0.1},
        },
    }
    conn.execute("INSERT INTO decisions VALUES (?, ?)", ("dec_learn_01", json.dumps(record)))
    conn.commit()
    conn.close()


def teardown_module() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    if MEM_PATH.exists():
        shutil.rmtree(MEM_PATH)


def test_learn_command() -> None:
    runner = CliRunner()

    # Run command
    result = runner.invoke(
        app,
        [
            "learn",
            "dec_learn_01",
            "--outcome",
            "FAILURE",
            "--severity",
            "5",
            "--db",
            str(DB_PATH),
            "--memory-path",
            str(MEM_PATH),
        ],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Learned from dec_learn_01" in result.stdout
    assert "Outcome: FAILURE (-1)" in result.stdout

    # Verify in LanceDB
    store = MemoryStore(db_path=MEM_PATH)
    # Search with dummy vector (won't match perfectly but we can fetch all or just check existence?)
    # LanceDB doesn't have "get by id" easily exposed in my client yet.
    # But I can access the table directly or use search with projected vector of same req.

    # Let's verify by checking table count or search.
    # We can reconstruct vector logic or just trust standard search works if we find logic.
    # Easiest: use invalid vector search with large limit? No.
    # We know the vector logic is deterministic.
    # But we can also inspect the table via duckdb/pandas if needed.

    tbl = store.db.open_table(store.table_name)
    df = tbl.to_pandas()
    assert len(df) == 1
    assert df.iloc[0]["decision_id"] == "dec_learn_01"
    assert df.iloc[0]["outcome"] == -1
    assert df.iloc[0]["severity"] == 5
