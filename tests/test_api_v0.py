from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from fastapi.testclient import TestClient

from lumyn.api.app import create_app
from lumyn.config import LumynSettings, ServiceSettings, Settings
from lumyn.store.sqlite import SqliteStore


def _settings(*, store_path: Path, signing_secret: str | None = None) -> Settings:
    return Settings(
        lumyn=LumynSettings(
            storage_url=f"sqlite:{store_path}",
            policy_path=Path("policies/lumyn-support.v0.yml"),
            mode="enforce",
            redaction_profile="default",
            top_k=5,
        ),
        service=ServiceSettings(signing_secret=signing_secret),
    )


def test_api_decide_persists_and_is_fetchable(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    app = create_app(settings=_settings(store_path=store_path))
    client = TestClient(app)

    request_obj = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "evidence": {"ticket_id": "ZD-4002"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }

    resp = client.post("/v0/decide", json=request_obj)
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


def test_api_v1_decide_returns_v1_record(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    app = create_app(settings=_settings(store_path=store_path))
    client = TestClient(app)

    request_obj = {
        "schema_version": "decision_request.v1",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "evidence": {"ticket_id": "ZD-4002"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }

    resp = client.post("/v1/decide", json=request_obj)
    assert resp.status_code == 200, resp.text
    record = resp.json()
    assert record["schema_version"] == "decision_record.v1"
    assert record["request"]["schema_version"] == "decision_request.v1"
    assert record["verdict"] in {"ALLOW", "DENY", "ABSTAIN", "ESCALATE"}

    decision_id = record["decision_id"]
    got = client.get(f"/v1/decisions/{decision_id}")
    assert got.status_code == 200
    fetched = got.json()
    assert fetched["schema_version"] == "decision_record.v1"
    assert fetched["decision_id"] == decision_id


def test_api_events_endpoint(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    app = create_app(settings=_settings(store_path=store_path))
    client = TestClient(app)

    request_obj = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "evidence": {"ticket_id": "ZD-4002"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        },
    }
    record = client.post("/v0/decide", json=request_obj).json()
    decision_id = record["decision_id"]

    resp = client.post(
        f"/v0/decisions/{decision_id}/events",
        json={"type": "label", "data": {"label": "failure", "summary": "Bad outcome"}},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert isinstance(payload.get("event_id"), str)


def test_api_policy_endpoint(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    app = create_app(settings=_settings(store_path=store_path))
    client = TestClient(app)

    resp = client.get("/v0/policy")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["policy_id"] == "lumyn-support"
    assert payload["policy_version"] == "0.1.0"
    assert payload["policy_hash"].startswith("sha256:")


def test_api_v1_policy_endpoint(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    app = create_app(settings=_settings(store_path=store_path))
    client = TestClient(app)

    resp = client.get("/v1/policy")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["policy_id"] == "lumyn-support"
    assert payload["policy_version"] == "0.1.0"
    assert payload["policy_hash"].startswith("sha256:")


def test_api_decide_requires_signature_when_configured(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    signing_key = "test-signing-key"
    app = create_app(settings=_settings(store_path=store_path, signing_secret=signing_key))
    client = TestClient(app)

    request_obj = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "evidence": {"ticket_id": "ZD-4002"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
        },
    }

    missing = client.post("/v0/decide", json=request_obj)
    assert missing.status_code == 401
    assert missing.json()["detail"]["reason_code"] == "AUTH_REQUIRED"

    body = json.dumps(request_obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    bad = client.post(
        "/v0/decide",
        content=body,
        headers={
            "content-type": "application/json",
            "X-Lumyn-Signature": "sha256:0" * 9,
        },
    )
    assert bad.status_code == 401
    assert bad.json()["detail"]["reason_code"] == "AUTH_INVALID_SIGNATURE"

    sig = "sha256:" + hmac.new(signing_key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    ok = client.post(
        "/v0/decide",
        content=body,
        headers={"content-type": "application/json", "X-Lumyn-Signature": sig},
    )
    assert ok.status_code == 200, ok.text


def test_api_v1_decide_requires_signature_when_configured(tmp_path: Path) -> None:
    store_path = tmp_path / "lumyn.db"
    signing_key = "test-signing-key"
    app = create_app(settings=_settings(store_path=store_path, signing_secret=signing_key))
    client = TestClient(app)

    request_obj = {
        "schema_version": "decision_request.v1",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "evidence": {"ticket_id": "ZD-4002"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
        },
    }

    missing = client.post("/v1/decide", json=request_obj)
    assert missing.status_code == 401
    assert missing.json()["detail"]["reason_code"] == "AUTH_REQUIRED"

    body = json.dumps(request_obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = "sha256:" + hmac.new(signing_key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    ok = client.post(
        "/v1/decide",
        content=body,
        headers={"content-type": "application/json", "X-Lumyn-Signature": sig},
    )
    assert ok.status_code == 200, ok.text
