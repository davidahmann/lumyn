from __future__ import annotations

from pathlib import Path

from lumyn import LumynConfig, decide
from lumyn.store.sqlite import SqliteStore


def test_decide_abstains_if_storage_unavailable(tmp_path: Path) -> None:
    cfg = LumynConfig(policy_path="policies/lumyn-support.v0.yml", store_path=tmp_path / "lumyn.db")

    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }

    store = SqliteStore(cfg.store_path)
    store.init()

    from typing import Any

    def _boom(_: dict[str, Any]) -> None:
        raise OSError("disk full")

    store.put_decision_record = _boom  # type: ignore[assignment]

    record = decide(request, config=cfg, store=store)
    assert record["verdict"] == "ABSTAIN"
    assert "STORAGE_UNAVAILABLE" in record["reason_codes"]


def test_decide_v1_abstains_if_storage_unavailable(tmp_path: Path) -> None:
    """Test that decide_v1 returns ABSTAIN when storage fails."""
    from lumyn.core.decide import decide_v1

    cfg = LumynConfig(policy_path="policies/starter.v1.yml", store_path=tmp_path / "lumyn.db")

    request = {
        "schema_version": "decision_request.v1",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }

    store = SqliteStore(cfg.store_path)
    store.init()

    from typing import Any

    def _boom(_: dict[str, Any]) -> None:
        raise OSError("disk full")

    store.put_decision_record = _boom  # type: ignore[assignment]

    record = decide_v1(request, config=cfg, store=store)
    assert record["verdict"] == "ABSTAIN"
    assert "STORAGE_UNAVAILABLE" in record["reason_codes"]
