from __future__ import annotations

from pathlib import Path

from lumyn import LumynConfig, decide
from lumyn.store.sqlite import SqliteStore


def test_decide_is_idempotent_with_request_id(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    cfg = LumynConfig(policy_path="policies/lumyn-support.v0.yml", store_path=store_path)

    request = {
        "schema_version": "decision_request.v0",
        "request_id": "req-1",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }

    r1 = decide(request, config=cfg)
    r2 = decide(request, config=cfg)
    assert r1["decision_id"] == r2["decision_id"]

    store = SqliteStore(store_path)
    stats = store.get_stats()
    assert stats.decisions == 1
