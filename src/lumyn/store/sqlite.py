from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import ulid


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load_schema_sql() -> str:
    schema_path = Path(__file__).with_name("schema.sql")
    return schema_path.read_text(encoding="utf-8")


@dataclass(frozen=True, slots=True)
class MemoryItem:
    memory_id: str
    tenant_id: str | None
    created_at: str
    label: str
    action_type: str
    feature: dict[str, Any]
    summary: str
    source_decision_id: str | None


@dataclass(frozen=True, slots=True)
class StoreStats:
    decisions: int
    decision_events: int
    memory_items: int
    policy_snapshots: int


class SqliteStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(_load_schema_sql())

    def put_decision_record(self, record: dict[str, Any]) -> None:
        decision_id = str(record["decision_id"])
        created_at = str(record["created_at"])

        request = record.get("request") or {}
        request_id = (
            request.get("request_id") if isinstance(request.get("request_id"), str) else None
        )
        subject = request.get("subject") or {}
        action = request.get("action") or {}
        target = action.get("target") or {}
        amount = action.get("amount") or {}
        context = request.get("context") or {}

        tenant_id = subject.get("tenant_id") if isinstance(subject.get("tenant_id"), str) else None
        subject_type = subject.get("type") if isinstance(subject.get("type"), str) else None
        subject_id = subject.get("id") if isinstance(subject.get("id"), str) else None

        action_type = str(action.get("type"))
        target_system = target.get("system") if isinstance(target.get("system"), str) else None
        target_resource_type = (
            target.get("resource_type") if isinstance(target.get("resource_type"), str) else None
        )
        target_resource_id = (
            target.get("resource_id") if isinstance(target.get("resource_id"), str) else None
        )

        amount_value: float | None
        if isinstance(amount.get("value"), int | float):
            amount_value = float(amount["value"])
        else:
            amount_value = None
        amount_currency = (
            amount.get("currency") if isinstance(amount.get("currency"), str) else None
        )

        context_digest = str(context.get("digest"))

        policy = record.get("policy") or {}
        policy_id = str(policy.get("policy_id"))
        policy_version = str(policy.get("policy_version"))
        policy_hash = str(policy.get("policy_hash"))

        verdict = str(record.get("verdict"))
        reason_codes = record.get("reason_codes") or []
        reason_codes_json = _json_dumps(reason_codes)

        record_json = _json_dumps(record)

        tenant_key = tenant_id or "__global__"

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO decisions (
                  decision_id, created_at, tenant_id,
                  subject_type, subject_id,
                  action_type,
                  target_system, target_resource_type, target_resource_id,
                  amount_value, amount_currency,
                  context_digest,
                  policy_id, policy_version, policy_hash,
                  verdict,
                  reason_codes_json,
                  record_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    created_at,
                    tenant_id,
                    subject_type,
                    subject_id,
                    action_type,
                    target_system,
                    target_resource_type,
                    target_resource_id,
                    amount_value,
                    amount_currency,
                    context_digest,
                    policy_id,
                    policy_version,
                    policy_hash,
                    verdict,
                    reason_codes_json,
                    record_json,
                ),
            )
            if request_id is not None:
                conn.execute(
                    """
                    INSERT INTO idempotency_keys (tenant_key, request_id, decision_id, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (tenant_key, request_id, decision_id, created_at),
                )

    def put_policy_snapshot(
        self,
        *,
        policy_hash: str,
        policy_id: str,
        policy_version: str,
        policy_text: str,
    ) -> None:
        created_at = _utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO policy_snapshots (
                  policy_hash, policy_id, policy_version, created_at, policy_text
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (policy_hash, policy_id, policy_version, created_at, policy_text),
            )

    def get_policy_snapshot(self, policy_hash: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT policy_text FROM policy_snapshots WHERE policy_hash = ?",
                (policy_hash,),
            ).fetchone()
            if row is None:
                return None
            return cast(str, row["policy_text"])

    def get_decision_record(self, decision_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT record_json FROM decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
            if row is None:
                return None
            return cast(dict[str, Any], json.loads(row["record_json"]))

    def get_decision_id_for_request_id(self, *, tenant_key: str, request_id: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT decision_id FROM idempotency_keys WHERE tenant_key = ? AND request_id = ?",
                (tenant_key, request_id),
            ).fetchone()
            if row is None:
                return None
            return cast(str, row["decision_id"])

    def append_decision_event(self, decision_id: str, event_type: str, data: dict[str, Any]) -> str:
        event_id = str(ulid.new())
        at = _utc_now_iso()
        data_json = _json_dumps(data)

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO decision_events (event_id, decision_id, at, type, data_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_id, decision_id, at, event_type, data_json),
            )
        return event_id

    def add_memory_item(
        self,
        *,
        tenant_id: str | None,
        label: str,
        action_type: str,
        feature: dict[str, Any],
        summary: str,
        source_decision_id: str | None,
        created_at: str | None = None,
        memory_id: str | None = None,
    ) -> MemoryItem:
        item = MemoryItem(
            memory_id=memory_id or str(ulid.new()),
            tenant_id=tenant_id,
            created_at=created_at or _utc_now_iso(),
            label=label,
            action_type=action_type,
            feature=feature,
            summary=summary,
            source_decision_id=source_decision_id,
        )

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_items (
                  memory_id,
                  tenant_id,
                  created_at,
                  label,
                  action_type,
                  feature_json,
                  summary,
                  source_decision_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.memory_id,
                    item.tenant_id,
                    item.created_at,
                    item.label,
                    item.action_type,
                    _json_dumps(item.feature),
                    item.summary,
                    item.source_decision_id,
                ),
            )

        return item

    def list_memory_items(
        self,
        *,
        tenant_id: str | None,
        action_type: str,
        label: str | None = None,
        limit: int = 500,
    ) -> list[MemoryItem]:
        if tenant_id is None and label is None:
            sql = (
                "SELECT memory_id, tenant_id, created_at, label, action_type, "
                "feature_json, summary, source_decision_id FROM memory_items "
                "WHERE action_type = ? AND tenant_id IS NULL "
                "ORDER BY created_at DESC LIMIT ?"
            )
            params: tuple[Any, ...] = (action_type, limit)
        elif tenant_id is None and label is not None:
            sql = (
                "SELECT memory_id, tenant_id, created_at, label, action_type, "
                "feature_json, summary, source_decision_id FROM memory_items "
                "WHERE action_type = ? AND tenant_id IS NULL AND label = ? "
                "ORDER BY created_at DESC LIMIT ?"
            )
            params = (action_type, label, limit)
        elif tenant_id is not None and label is None:
            sql = (
                "SELECT memory_id, tenant_id, created_at, label, action_type, "
                "feature_json, summary, source_decision_id FROM memory_items "
                "WHERE action_type = ? AND tenant_id = ? "
                "ORDER BY created_at DESC LIMIT ?"
            )
            params = (action_type, tenant_id, limit)
        else:
            sql = (
                "SELECT memory_id, tenant_id, created_at, label, action_type, "
                "feature_json, summary, source_decision_id FROM memory_items "
                "WHERE action_type = ? AND tenant_id = ? AND label = ? "
                "ORDER BY created_at DESC LIMIT ?"
            )
            params = (action_type, tenant_id, label, limit)

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        items: list[MemoryItem] = []
        for row in rows:
            items.append(
                MemoryItem(
                    memory_id=row["memory_id"],
                    tenant_id=row["tenant_id"],
                    created_at=row["created_at"],
                    label=row["label"],
                    action_type=row["action_type"],
                    feature=json.loads(row["feature_json"]),
                    summary=row["summary"],
                    source_decision_id=row["source_decision_id"],
                )
            )
        return items

    def get_stats(self) -> StoreStats:
        with self.connect() as conn:
            decisions = int(conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0])
            events = int(conn.execute("SELECT COUNT(*) FROM decision_events").fetchone()[0])
            memory = int(conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0])
            policy_snapshots = int(
                conn.execute("SELECT COUNT(*) FROM policy_snapshots").fetchone()[0]
            )
        return StoreStats(
            decisions=decisions,
            decision_events=events,
            memory_items=memory,
            policy_snapshots=policy_snapshots,
        )
