PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS decisions (
  decision_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  tenant_id TEXT,
  subject_type TEXT,
  subject_id TEXT,
  action_type TEXT NOT NULL,
  target_system TEXT,
  target_resource_type TEXT,
  target_resource_id TEXT,
  amount_value REAL,
  amount_currency TEXT,
  context_digest TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  policy_hash TEXT NOT NULL,
  verdict TEXT NOT NULL,
  reason_codes_json TEXT NOT NULL,
  record_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions (created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_tenant_created_at ON decisions (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_action_created_at ON decisions (action_type, created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_verdict_created_at ON decisions (verdict, created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_context_digest ON decisions (context_digest);
CREATE INDEX IF NOT EXISTS idx_decisions_target ON decisions (target_system, target_resource_id);

CREATE TABLE IF NOT EXISTS decision_events (
  event_id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  at TEXT NOT NULL,
  type TEXT NOT NULL,
  data_json TEXT NOT NULL,
  FOREIGN KEY (decision_id) REFERENCES decisions(decision_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_decision_events_decision_id_at ON decision_events (decision_id, at);

CREATE TABLE IF NOT EXISTS memory_items (
  memory_id TEXT PRIMARY KEY,
  tenant_id TEXT,
  created_at TEXT NOT NULL,
  label TEXT NOT NULL,
  action_type TEXT NOT NULL,
  feature_json TEXT NOT NULL,
  summary TEXT NOT NULL,
  source_decision_id TEXT,
  FOREIGN KEY (source_decision_id) REFERENCES decisions(decision_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_items_lookup ON memory_items (tenant_id, action_type, label, created_at);

CREATE TABLE IF NOT EXISTS policy_snapshots (
  policy_hash TEXT PRIMARY KEY,
  policy_id TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  policy_text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_policy_snapshots_created_at ON policy_snapshots (created_at);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  tenant_key TEXT NOT NULL,
  request_id TEXT NOT NULL,
  decision_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (tenant_key, request_id),
  FOREIGN KEY (decision_id) REFERENCES decisions(decision_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_created_at ON idempotency_keys (created_at);
