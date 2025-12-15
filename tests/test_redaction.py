from __future__ import annotations

from typing import Any

from lumyn.engine.redaction import redact_request_for_persistence


def test_redaction_default_removes_sensitive_inline_keys_deterministically() -> None:
    request: dict[str, Any] = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "context": {
            "mode": "inline",
            "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "inline": {"prompt": "secret", "keep_me": "ok", "email": "a@b.c"},
        },
    }

    out1 = redact_request_for_persistence(request, profile="default")
    out2 = redact_request_for_persistence(request, profile="default")

    assert out1.fields_removed == out2.fields_removed
    assert out1.fields_removed == ["/context/inline/email", "/context/inline/prompt"]
    assert "prompt" not in out1.request["context"]["inline"]
    assert "email" not in out1.request["context"]["inline"]
    assert out1.request["context"]["inline"]["keep_me"] == "ok"


def test_redaction_strict_removes_all_inline_keys() -> None:
    request: dict[str, Any] = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent"},
        "action": {"type": "support.update_ticket", "intent": "Update ticket"},
        "context": {
            "mode": "inline",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "inline": {"a": 1, "b": 2},
        },
    }
    out = redact_request_for_persistence(request, profile="strict")
    assert out.request["context"]["inline"] == {}
    assert out.fields_removed == ["/context/inline/a", "/context/inline/b"]
