from __future__ import annotations

import json
import logging
from typing import Any

from lumyn.telemetry.logging import log_decision_record


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(str(record.getMessage()))


def test_log_decision_record_is_safe() -> None:
    record: dict[str, Any] = {
        "schema_version": "decision_record.v0",
        "decision_id": "01TESTDECISIONID0000000000000000",
        "created_at": "2026-01-01T00:00:00Z",
        "request": {
            "schema_version": "decision_request.v0",
            "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
            "action": {"type": "support.refund", "intent": "Refund", "tags": ["x"]},
            "evidence": {"raw": {"should_not": "appear"}},
            "context": {
                "mode": "inline",
                "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "inline": {"prompt": "super secret"},
            },
        },
        "policy": {"policy_id": "p", "policy_version": "0", "policy_hash": "sha256:bb" * 17},
        "verdict": "ESCALATE",
        "reason_codes": ["X"],
        "determinism": {"inputs_digest": "sha256:cc" * 17},
    }

    logger = logging.getLogger("lumyn.test")
    logger.setLevel(logging.INFO)
    handler = _ListHandler()
    logger.addHandler(handler)
    try:
        log_decision_record(record, logger=logger)
    finally:
        logger.removeHandler(handler)

    assert len(handler.messages) == 1
    payload = json.loads(handler.messages[0])
    assert payload["decision_id"] == record["decision_id"]
    assert "request" not in payload
    assert "evidence" not in payload
    assert "super secret" not in handler.messages[0]
    assert "should_not" not in handler.messages[0]
