from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from lumyn.api.app import ApiConfig, create_app
from lumyn.store.sqlite import SqliteStore


def test_api_decide_persists_and_is_fetchable(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    cfg = ApiConfig(
        policy_path=Path("policies/lumyn-support.v0.yml"), store_path=store_path, top_k=5
    )
    app = create_app(config=cfg)
    client = TestClient(app)

    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "evidence": {"ticket_id": "ZD-4002"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }

    resp = client.post("/v0/decide", json=request)
    assert resp.status_code == 200, resp.text
    record = resp.json()
    assert record["schema_version"] == "decision_record.v0"

    decision_id = record["decision_id"]
    got = client.get(f"/v0/decisions/{decision_id}")
    assert got.status_code == 200
    assert got.json()["decision_id"] == decision_id

    store = SqliteStore(store_path)
    persisted = store.get_decision_record(decision_id)
    assert persisted is not None


def test_api_events_endpoint(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    cfg = ApiConfig(
        policy_path=Path("policies/lumyn-support.v0.yml"), store_path=store_path, top_k=5
    )
    app = create_app(config=cfg)
    client = TestClient(app)

    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "evidence": {"ticket_id": "ZD-4002"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        },
    }
    record = client.post("/v0/decide", json=request).json()
    decision_id = record["decision_id"]

    resp = client.post(
        f"/v0/decisions/{decision_id}/events",
        json={"type": "label", "data": {"label": "failure", "summary": "Bad outcome"}},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert isinstance(payload.get("event_id"), str)
