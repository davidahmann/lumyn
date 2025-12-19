# Lumyn Specs & Schemas

This document is the canonical definition of Lumyn’s contracts and deterministic semantics.

**Current Stable Version: v1.0.0**

## Design invariants

- **Decision Record is the system-of-record** (telemetry is not).
- **Deterministic outputs**: same inputs + policy + memory snapshot ⇒ same normalized record.
- **No bluffing**: uncertainty yields `ABSTAIN | ESCALATE | DENY` with stable reason codes.
- **Append-only updates**: outcomes/labels/overrides append events; original decision is immutable.

## Versioning policy

- `decision_request.v1` and `decision_record.v1` are public contracts.
- Changes are **additive only**. Breaking changes require `*.v2`.
- v0 contracts are **deprecated** but supported for legacy read/write.

---

# Lumyn Specs (v1)

## v1 Verdict Model

v1 uses the four-outcome model:
- **ALLOW**: Safe to proceed.
- **DENY**: Block the action (until evidence provided).
- **ABSTAIN**: System cannot safely decide (error, missing critical data, hard block).
- **ESCALATE**: Requires human review.

## Deterministic IDs & Digests

### IDs
- `decision_id`: ULID (sortable, collision-resistant)
- `event_id`: ULID

### Digests (RFC 8785)
All digests are `sha256:<hex>` computed via JSON Canonicalization Scheme (JCS).

- `policy.policy_hash`: SHA-256 of canonicalized policy JSON.
- `determinism.inputs_digest`: SHA-256 of canonicalized payload containing:
    - `request` (as persisted in the Decision Record)
    - `derived` evaluation features (e.g. `amount_usd`, FX presence)

## Policy (v1) — YAML spec

Canonical specification for `policy.v1`.

### Top-level fields
- `schema_version`: `policy.v1` (required)
- `policy_id`: string (required)
- `policy_version`: semver string (required)
- `defaults`:
  - `mode`: `enforce|advisory`
  - `default_verdict`: `ESCALATE` (recommended)
  - `default_reason_code`: string (required)
- `rules`: list of rule objects

### Evaluation Stages (Strict Order)
1. `REQUIREMENTS`: Input validation. (Typical: `DENY` "Missing Evidence", `ABSTAIN` "Bad Request")
2. `HARD_BLOCKS`: Sanctions, embargoes. (Typical: `ABSTAIN`, `DENY`)
3. `ESCALATIONS`: Business logic requiring human review. (Typical: `ESCALATE`)
4. `ALLOW_PATHS`: Safe lists, VIPs. (Typical: `ALLOW`)
5. `DEFAULT`: Fallback.

### Rule Object
- `id`: string (required)
- `stage`: `REQUIREMENTS | HARD_BLOCKS | ESCALATIONS | ALLOW_PATHS`
- `when`: predicate (e.g. `action_type: "refund"`)
- `if` / `if_all` / `if_any`: condition blocks
- `then`:
  - `verdict`: `ALLOW | DENY | ABSTAIN | ESCALATE`
  - `reason_codes`: list[strings]
  - `queries`: list[{field, question}] (optional)
  - `obligations`: list[objects] (optional)

### Supported Conditions (Strict)
- `action_type`
- `amount_currency`, `amount_currency_ne`
- `amount_usd`, `amount_usd_gt/gte/lt/lte`
- `evidence.<key>_is`, `_ne`, `_in` (list)
- `evidence.<key>_gt/gte/lt/lte` (numeric)

### Verdict Precedence
If multiple rules match across stages:
`ABSTAIN` > `DENY` > `ESCALATE` > `ALLOW`

---

# Legacy Specs (v0)

> [!WARNING]
> **Deprecated**: v0 is deprecated. New integrations should use v1.

## DecisionRequest (v0)
`schemas/decision_request.v0.schema.json`

## DecisionRecord (v0)
`schemas/decision_record.v0.schema.json`

## Policy (v0)
`schemas/policy.v0.schema.json`

## Verdicts (v0)
- `TRUST` (mapped to `ALLOW`)
- `QUERY` (mapped to `DENY`)
- `ABSTAIN`
- `ESCALATE`

## v0 Evaluation
5 stages: `REQUIREMENTS → HARD_BLOCKS → ESCALATIONS → TRUST_PATHS → DEFAULT`.
Precedence: `ABSTAIN > QUERY > ESCALATE > TRUST`.
