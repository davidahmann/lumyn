# Lumyn Specs & Schemas (v0)

This document is the canonical definition of Lumyn’s v0 contracts and deterministic semantics.

## Design invariants

- **Decision Record is the system-of-record** (telemetry is not).
- **Deterministic outputs**: same inputs + policy + memory snapshot ⇒ same normalized record.
- **No bluffing**: uncertainty yields `ABSTAIN | ESCALATE | QUERY` with stable reason codes.
- **Append-only updates**: outcomes/labels/overrides append events; original decision is immutable.

## Versioning policy (future-proofing)

- `decision_request.v0` and `decision_record.v0` are public contracts.
- v0 changes are **additive only** (new optional fields). Breaking changes require `*.v1`.
- New experimental fields go under `extensions` (namespaced keys) to prevent core schema churn.

## Deterministic IDs, canonicalization, and digests

### IDs

- `decision_id`: ULID (sortable, collision-resistant)
- `event_id`: ULID (for appended decision events)

### Canonical JSON

All digests use RFC 8785 JSON Canonicalization Scheme (JCS) on a JSON-equivalent structure.

### Digests

All digests are formatted as `sha256:<hex>`.

- `request.context.digest`: sha256 of canonicalized context payload (inline) or canonicalized reference tuple (reference).
- `policy.policy_hash`: sha256 of canonicalized policy JSON (YAML parsed → JSON-equivalent → JCS).
- `determinism.inputs_digest`: sha256 of canonicalized normalized request + derived evaluation features.

## Verdicts

- `TRUST`: proceed automatically
- `ABSTAIN`: hard stop (block)
- `ESCALATE`: require human approval/review
- `QUERY`: request more evidence/confirmation (no action taken)

### Verdict precedence (v0)

To keep behavior predictable, Lumyn evaluates all applicable rules and then computes a final
verdict with fixed precedence:

`ABSTAIN` > `QUERY` > `ESCALATE` > `TRUST`

Rationale: if we cannot safely evaluate due to missing evidence, we prefer actionable questions
(`QUERY`) over immediate human escalation; hard blocks still win.

## Reason codes (contract)

- Stable strings, recommended format: `UPPER_SNAKE_CASE`
- No dynamic content inside the reason code (put details in `explanation.details`).
- Every Decision Record MUST contain at least one reason code.
- There must always be a safe default reason code for no-match outcomes:
  - `NO_MATCH_DEFAULT_ESCALATE`
- Engine-reserved reason codes (not policy-specific):
  - `INVALID_REQUEST_SCHEMA`
  - `INVALID_POLICY`
  - `STORAGE_UNAVAILABLE`

## DecisionRequest (v0) — JSON Schema

`schemas/decision_request.v0.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://lumyn.dev/schemas/decision_request.v0.schema.json",
  "title": "Lumyn DecisionRequest (v0)",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "subject", "action", "context"],
  "properties": {
    "schema_version": { "type": "string", "const": "decision_request.v0" },
    "request_id": { "type": "string", "description": "Optional idempotency key (ULID/UUID)." },

    "trace": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "correlation_id": { "type": "string" },
        "span_id": { "type": "string" }
      }
    },

    "tenant": {
      "type": "object",
      "additionalProperties": false,
      "required": ["tenant_id"],
      "properties": {
        "tenant_id": { "type": "string", "minLength": 1 },
        "environment": { "type": "string", "enum": ["dev", "staging", "prod"] }
      }
    },

    "subject": {
      "type": "object",
      "additionalProperties": false,
      "required": ["type", "id"],
      "properties": {
        "type": { "type": "string", "enum": ["service", "agent", "user", "job"] },
        "id": { "type": "string", "minLength": 1 },
        "tenant_id": { "type": "string" },
        "ip": { "type": "string" },
        "user_agent": { "type": "string" },
        "roles": { "type": "array", "items": { "type": "string" }, "default": [] }
      }
    },

    "action": {
      "type": "object",
      "additionalProperties": false,
      "required": ["type", "intent"],
      "properties": {
        "type": {
          "type": "string",
          "description": "Namespaced action type, e.g. support.refund, support.close_ticket.",
          "pattern": "^[a-z0-9]+(\\\u002e[a-z0-9_]+)+$"
        },
        "intent": { "type": "string", "minLength": 1 },
        "target": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "system": { "type": "string" },
            "resource_type": { "type": "string" },
            "resource_id": { "type": "string" }
          }
        },
        "amount": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "value": { "type": "number" },
            "currency": { "type": "string", "minLength": 3, "maxLength": 3 }
          }
        },
        "tags": { "type": "array", "items": { "type": "string" }, "default": [] }
      }
    },

    "evidence": {
      "type": "object",
      "description": "Caller-provided structured signals; Lumyn does not fetch external data in v1.",
      "additionalProperties": true,
      "default": {}
    },

    "context": {
      "type": "object",
      "additionalProperties": false,
      "required": ["mode", "digest"],
      "properties": {
        "mode": { "type": "string", "enum": ["digest_only", "inline", "reference"] },
        "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
        "ref": {
          "type": "object",
          "additionalProperties": false,
          "required": ["kind", "id"],
          "properties": {
            "kind": { "type": "string" },
            "id": { "type": "string" },
            "uri": { "type": "string" }
          }
        },
        "inline": { "type": "object", "additionalProperties": true },
        "redaction": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "profile": { "type": "string", "description": "default|strict|off" },
            "fields_removed": { "type": "array", "items": { "type": "string" }, "default": [] }
          }
        }
      },
      "allOf": [
        { "if": { "properties": { "mode": { "const": "inline" } } }, "then": { "required": ["inline"] } },
        { "if": { "properties": { "mode": { "const": "reference" } } }, "then": { "required": ["ref"] } }
      ]
    },

    "policy": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "policy_id": { "type": "string" },
        "policy_version": { "type": "string" },
        "mode": { "type": "string", "enum": ["enforce", "advisory"] }
      }
    },

    "hints": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "mode": { "type": "string", "enum": ["enforce", "advisory"] },
        "dry_run": { "type": "boolean", "default": false }
      }
    },

    "extensions": { "type": "object", "additionalProperties": true, "default": {} }
  }
}
```

## DecisionRecord (v0) — JSON Schema

`schemas/decision_record.v0.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://lumyn.dev/schemas/decision_record.v0.schema.json",
  "title": "Lumyn DecisionRecord (v0)",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "decision_id",
    "created_at",
    "request",
    "policy",
    "verdict",
    "reason_codes",
    "matched_rules",
    "risk_signals",
    "determinism"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "decision_record.v0" },
    "decision_id": { "type": "string", "description": "ULID recommended.", "minLength": 10 },
    "created_at": { "type": "string", "format": "date-time" },

    "trace": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "correlation_id": { "type": "string" },
        "span_id": { "type": "string" }
      }
    },

    "request": { "$ref": "https://lumyn.dev/schemas/decision_request.v0.schema.json" },

    "policy": {
      "type": "object",
      "additionalProperties": false,
      "required": ["policy_id", "policy_version", "policy_hash", "mode"],
      "properties": {
        "policy_id": { "type": "string" },
        "policy_version": { "type": "string" },
        "policy_hash": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
        "mode": { "type": "string", "enum": ["enforce", "advisory"] }
      }
    },

    "verdict": { "type": "string", "enum": ["TRUST", "ABSTAIN", "ESCALATE", "QUERY"] },

    "reason_codes": {
      "type": "array",
      "minItems": 1,
      "items": { "type": "string" },
      "description": "Stable machine-readable explanations."
    },

    "matched_rules": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["rule_id", "stage", "effect"],
        "properties": {
          "rule_id": { "type": "string" },
          "stage": { "type": "string", "enum": ["REQUIREMENTS", "HARD_BLOCKS", "ESCALATIONS", "TRUST_PATHS", "DEFAULT"] },
          "effect": { "type": "string", "enum": ["TRUST", "ABSTAIN", "ESCALATE", "QUERY", "NOOP"] },
          "reason_codes": { "type": "array", "items": { "type": "string" }, "default": [] }
        }
      },
      "default": []
    },

    "risk_signals": {
      "type": "object",
      "additionalProperties": false,
      "required": ["uncertainty_score", "failure_similarity"],
      "properties": {
        "uncertainty_score": { "type": "number", "minimum": 0, "maximum": 1 },
        "failure_similarity": {
          "type": "object",
          "additionalProperties": false,
          "required": ["score", "top_k"],
          "properties": {
            "score": { "type": "number", "minimum": 0, "maximum": 1 },
            "top_k": {
              "type": "array",
              "items": {
                "type": "object",
                "additionalProperties": false,
                "required": ["memory_id", "label", "score"],
                "properties": {
                  "memory_id": { "type": "string" },
                  "label": { "type": "string", "enum": ["failure", "success", "near_miss"] },
                  "score": { "type": "number", "minimum": 0, "maximum": 1 },
                  "summary": { "type": "string" }
                }
              },
              "default": []
            }
          }
        },
        "ood_score": { "type": "number", "minimum": 0, "maximum": 1 },
        "drift_flag": { "type": "boolean" }
      }
    },

    "queries": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["field", "question"],
        "properties": { "field": { "type": "string" }, "question": { "type": "string" } }
      },
      "default": []
    },

    "obligations": {
      "type": "array",
      "items": { "type": "object", "additionalProperties": true },
      "default": []
    },

    "explanation": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "summary": { "type": "string" },
        "details": { "type": "string" }
      }
    },

    "decision_event_log": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["event_id", "at", "type"],
        "properties": {
          "event_id": { "type": "string" },
          "at": { "type": "string", "format": "date-time" },
          "type": { "type": "string", "enum": ["outcome", "label", "note", "override"] },
          "data": { "type": "object", "additionalProperties": true }
        }
      },
      "default": []
    },

    "links": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "context_id": { "type": "string" },
        "proof_id": { "type": "string" }
      }
    },

    "determinism": {
      "type": "object",
      "additionalProperties": false,
      "required": ["engine_version", "evaluation_order", "inputs_digest"],
      "properties": {
        "engine_version": { "type": "string" },
        "evaluation_order": {
          "type": "array",
          "items": { "type": "string", "enum": ["REQUIREMENTS", "HARD_BLOCKS", "ESCALATIONS", "TRUST_PATHS", "DEFAULT"] }
        },
        "inputs_digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
        "memory_snapshot": { "type": "string", "description": "Identifier for the memory state used (implementation-defined)." }
      }
    },

    "extensions": { "type": "object", "additionalProperties": true, "default": {} }
  }
}
```

## Policy (v0) — YAML spec

Policy is intentionally boring and deterministic. It does not execute code; it selects verdicts
based on structured conditions over the request and risk signals.

### Top-level fields

- `schema_version`: `policy.v0`
- `policy_id`: stable id (string)
- `policy_version`: semver-ish string
- `defaults`:
  - `mode`: `enforce|advisory`
  - `default_verdict`: recommended `ESCALATE`
  - `default_reason_code`: required (e.g. `NO_MATCH_DEFAULT_ESCALATE`)
- `thresholds`: arbitrary numeric constants referenced by rules
- `required_evidence`: map from `action.type` → list of evidence keys required to avoid `QUERY`
- `rules[]`: ordered list of rule objects

### Rule fields

- `id`: stable rule identifier (e.g. `R007`)
- `stage`: `REQUIREMENTS|HARD_BLOCKS|ESCALATIONS|TRUST_PATHS`
- `when`: match predicate (at minimum supports `action.type`)
- `if` / `if_all` / `if_any`: condition blocks
- `then`: effect:
  - `verdict`: `TRUST|ABSTAIN|ESCALATE|QUERY`
  - `reason_codes`: list of codes (stable)
  - optional `queries[]` for `QUERY` (field + question)
  - optional `obligations[]` for non-TRUST (implementation-defined objects)

### Deterministic evaluation semantics

1) Validate request schema.
2) Derive evaluation features (e.g., amount normalization); compute `inputs_digest`.
3) Compute risk signals (uncertainty, failure similarity, optional OOD/drift).
4) Evaluate all rules in fixed stage order:
   `REQUIREMENTS → HARD_BLOCKS → ESCALATIONS → TRUST_PATHS → DEFAULT`
5) Collect `matched_rules` and accumulate `reason_codes` in evaluation order.
6) Compute final verdict using precedence:
   `ABSTAIN > QUERY > ESCALATE > TRUST`
7) If no rule fires, apply defaults (`DEFAULT` stage) and add `default_reason_code`.

## Experience Memory (MVP)

Lumyn stores labeled experiences and uses them as negative/positive evidence.

Each memory item includes:
- `memory_id` (ULID)
- `label`: `failure|success|near_miss`
- `action.type`
- `feature_json` (normalized features used for similarity)
- `summary` (human-readable)
- optional `source_decision_id`

Similarity MVP: deterministic feature overlap (e.g., weighted Jaccard), filtered by tenant and action type.
Tie-breakers must be stable (e.g., sort by score desc then `memory_id` asc).

## Storage model (MVP)

Default persistence is local-first SQLite. The store must support:
- durable decision records (persist before returning success)
- append-only events (labels/outcomes/notes/overrides)
- experience memory items for similarity

Recommended tables (SQLite + Postgres-compatible):
- `decisions`
  - primary: `decision_id`
  - indexed: `(tenant_id, created_at)`, `(action_type, created_at)`, `(verdict, created_at)`, `(context_digest)`
  - store full record JSON in `record_json` for export/replay
- `decision_events`
  - primary: `event_id`
  - indexed: `(decision_id, at)`
- `memory_items`
  - primary: `memory_id`
  - indexed: `(tenant_id, action_type, label, created_at)`

## Service API (v0)

Service mode is an optional wrapper around the same core as library mode.

- `POST /v0/decide` → returns `DecisionRecord` v0 (must persist before returning 200)
- `GET /v0/decisions/{decision_id}` → returns `DecisionRecord` v0
- `POST /v0/decisions/{decision_id}/events` → appends event; returns updated record or `event_id`
- `GET /v0/policy` → returns loaded policy `{policy_id, policy_version, policy_hash}`

## CLI contract (v0)

- `lumyn init` — scaffold starter policy + local SQLite workspace
- `lumyn demo` — emit real-looking Decision Records and show verdict pathways
- `lumyn decide --in request.json [--out record.json]` — produce a Decision Record
- `lumyn show <decision_id>` — print raw Decision Record JSON
- `lumyn explain <decision_id>` — print stable human summary
- `lumyn export <decision_id> [--out pack.zip]` — export record (and optional “decision pack”)
- `lumyn label <decision_id> --failure|--success|--near-miss --note "..."` — append label event + memory item
- `lumyn policy validate <policy.yml>` — schema + reason code validation
- `lumyn doctor` — environment + policy + store checks

## Decision pack export (v0)

Export is designed for incident workflows (attach to tickets, paste into postmortems).

Minimum export:
- `decision_record.json` (schema-valid DecisionRecord)

Optional “pack” (zip):
- `decision_record.json`
- `policy.yml` (the exact loaded policy)
- `vectors.json` (optional: the input request + normalized output for regression reproduction)
- `README.txt` (how to replay/validate)

## Security & privacy defaults

- Default `request.context.mode` SHOULD be `digest_only` in production integrations.
- If `inline` context is provided, the store SHOULD support configurable redaction prior to persistence.
- Service mode MAY support request signing (e.g., shared-secret HMAC) but should not be required for local-first PLG.
