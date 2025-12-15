from __future__ import annotations

from pathlib import Path

from lumyn.core.decide import LumynConfig, decide
from lumyn.store.sqlite import SqliteStore


def test_decide_redacts_inline_before_persistence(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    cfg = LumynConfig(
        policy_path="policies/lumyn-support.v0.yml",
        store_path=store_path,
        redaction_profile="strict",
    )

    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "context": {
            "mode": "inline",
            "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "inline": {"prompt": "secret", "email": "a@b.c", "keep": "x"},
        },
    }

    record = decide(request, config=cfg)
    persisted_request = record["request"]
    assert persisted_request["context"]["inline"] == {}
    assert persisted_request["context"]["redaction"]["profile"] == "strict"
    assert persisted_request["context"]["redaction"]["fields_removed"] == [
        "/context/inline/email",
        "/context/inline/keep",
        "/context/inline/prompt",
    ]

    store = SqliteStore(store_path)
    stored = store.get_decision_record(record["decision_id"])
    assert stored is not None
    assert stored["request"]["context"]["inline"] == {}
