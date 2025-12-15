# Lumyn

**Decision Records for production AI.**

Lumyn is a deterministic `decide()` gateway for AI systems that take real actions (refunds,
ticket operations, account changes). Instead of “the model said so,” Lumyn returns a
verdict — `TRUST | ABSTAIN | ESCALATE | QUERY` — and writes a durable **Decision Record**
you can export, replay, and verify under incident pressure.

`decide -> record -> export -> replay`

## When an AI incident happens

Support shares a screenshot.
Engineering tries to reconstruct what the model saw and what policy/risk rules fired.
Nobody can answer, precisely and repeatably: what happened, what changed, and why did we allow it?

Lumyn’s unit of evidence is a `decision_id`. Paste it into the ticket, then:

- `lumyn show <decision_id>`
- `lumyn explain <decision_id> --markdown`
- `lumyn export <decision_id> --pack --out decision_pack.zip`
- `lumyn replay decision_pack.zip --markdown`

## Why teams adopt Lumyn

- **Write-path safety**: gates consequential actions with explicit policy and outcomes.
- **Replayable decisions**: stable digests (`policy.policy_hash`, `request.context.digest`, `determinism.inputs_digest`).
- **No bluffing**: uncertainty becomes `ABSTAIN`, `ESCALATE`, or `QUERY` with reason codes.
- **Compounding reliability**: labeled failures/successes feed Experience Memory similarity.
- **Drop-in**: works as a Python library and as an optional HTTP service.

## The primitive

You wrap a risky action with `decide()`:

1) you provide a `DecisionRequest` (subject, action, evidence, `context.digest`)
2) Lumyn evaluates deterministic policy + risk signals + Experience Memory similarity
3) Lumyn returns a `DecisionRecord` and persists it (append-only)

The Decision Record is the unit you export into incidents, tickets, and postmortems.

## How it works (one screen)

- You provide a `DecisionRequest` (no external fetches in v0; your app supplies `evidence`).
- Lumyn evaluates policy deterministically (fixed stages + stable reason codes).
- Lumyn computes Experience Memory similarity from prior labeled outcomes.
- Lumyn persists the Decision Record to SQLite before returning (or returns ABSTAIN on storage failure).

## What a Decision Record looks like

```json
{
  "schema_version": "decision_record.v0",
  "decision_id": "01JZ1S7Y1NQ2A0D5JQK2Q2P3X4",
  "created_at": "2025-12-15T10:00:00Z",
  "request": {
    "schema_version": "decision_request.v0",
    "subject": { "type": "service", "id": "support-agent", "tenant_id": "acme" },
    "action": {
      "type": "support.refund",
      "intent": "Refund duplicate charge for order 82731",
      "target": { "system": "stripe", "resource_type": "charge", "resource_id": "ch_123" },
      "amount": { "value": 201.0, "currency": "USD" },
      "tags": ["duplicate_charge"]
    },
    "evidence": { "ticket_id": "ZD-1001", "order_id": "82731", "customer_id": "C-9" },
    "context": { "mode": "digest_only", "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
  },
  "policy": {
    "policy_id": "lumyn-support",
    "policy_version": "0.1.0",
    "policy_hash": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "mode": "enforce"
  },
  "verdict": "ESCALATE",
  "reason_codes": ["REFUND_OVER_ESCALATION_LIMIT"],
  "matched_rules": [
    { "rule_id": "R008", "stage": "ESCALATIONS", "effect": "ESCALATE", "reason_codes": ["REFUND_OVER_ESCALATION_LIMIT"] }
  ],
  "risk_signals": {
    "uncertainty_score": 0.12,
    "failure_similarity": { "score": 0.07, "top_k": [] }
  },
  "determinism": {
    "engine_version": "0.1.0",
    "evaluation_order": ["REQUIREMENTS", "HARD_BLOCKS", "ESCALATIONS", "TRUST_PATHS", "DEFAULT"],
    "inputs_digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  }
}
```

## Quickstart (no keys, no Docker)

Install:
- `pip install lumyn`
- Service mode: `pip install lumyn[service]`

Fastest “aha” (compounding in seconds):

- `lumyn doctor --fix`
- `lumyn demo --story`

Common CLI workflows:
- `lumyn init` (creates local SQLite + starter policy)
- `lumyn demo` (emits a few real-looking Decision Records as JSON)
- `lumyn demo --story` (auto-label a failure and show compounding)
- `lumyn decide --in request.json` (prints a Decision Record)
- `lumyn show <decision_id>`, `lumyn explain <decision_id>`, `lumyn export <decision_id>`
- `lumyn export <decision_id> --pack --out decision_pack.zip`
- `lumyn replay decision_pack.zip` (validate pack + digests)
- `lumyn label <decision_id> --label failure --summary "Bad outcome in prod"`
- `lumyn policy validate` (validates `.lumyn/policy.yml`) or `lumyn policy validate --path ./policy.yml`
- `lumyn doctor` / `lumyn doctor --fix` (workspace health + repairs)
- `lumyn serve --dry-run` / `lumyn serve` (run FastAPI service)

## SDK (drop-in)

Lumyn does not call your model. You call Lumyn before (or around) a real write-path action.

```python
from lumyn import LumynConfig, decide

cfg = LumynConfig(store_path=".lumyn/lumyn.db")  # default policy is built-in

record = decide(
    {
        "schema_version": "decision_request.v0",
        "request_id": "req_123",  # recommended for retries/idempotency
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {
            "type": "support.refund",
            "intent": "Refund duplicate charge for order 82731",
            "amount": {"value": 12.0, "currency": "USD"},
            "tags": ["duplicate_charge"],
        },
        "evidence": {
            "ticket_id": "ZD-1001",
            "order_id": "82731",
            "customer_id": "C-9",
            "customer_age_days": 180,
            "previous_refund_count_90d": 0,
            "chargeback_risk": 0.05,
            "payment_instrument_risk": "low",
        },
        "context": {"mode": "digest_only", "digest": "sha256:" + ("a" * 64)},
    },
    config=cfg,
)

if record["verdict"] == "TRUST":
    pass  # perform the write-path action
else:
    pass  # block/escalate/ask for evidence based on verdict + reason_codes + queries
```

## Service mode (FastAPI)

Run:
- `lumyn serve --dry-run`
- `lumyn serve --host 127.0.0.1 --port 8000`

Call:

`curl -sS -X POST http://127.0.0.1:8000/v0/decide -H 'content-type: application/json' --data-binary @request.json | jq .`

Endpoints:
- `POST /v0/decide` -> DecisionRecord
- `GET /v0/decisions/{decision_id}`
- `POST /v0/decisions/{decision_id}/events`
- `GET /v0/policy`

Optional request signing:
- Set `LUMYN_SIGNING_SECRET`
- Send `X-Lumyn-Signature: sha256:<hmac(body_bytes)>` over the exact bytes you send

## Policy packs (starter templates)

Bundled policies are safe defaults you can copy and customize:
- `policies/lumyn-support.v0.yml` (support/refund + ticket workflows)
- `policies/packs/lumyn-account.v0.yml` (account change email)
- `policies/packs/lumyn-billing.v0.yml` (billing approve spend)

Create a workspace with a specific pack:

- `lumyn init --workspace .lumyn-account --policy-template policies/packs/lumyn-account.v0.yml`
- `lumyn init --workspace .lumyn-billing --policy-template policies/packs/lumyn-billing.v0.yml`

Validate:
- `lumyn policy validate --workspace .lumyn-account`

## What Lumyn is / isn’t

Lumyn is:
- A deterministic decision gateway + durable Decision Records for incidents/audit/debugging
- A small policy engine with stable reason codes and replayable digests

Lumyn is not:
- An agent framework
- A monitoring dashboard
- A data-fetching risk engine (v0 does not call external systems; you provide evidence)

## Operational notes (hair-on-fire defaults)

- **Idempotency**: set `request_id` on `DecisionRequest` so retries return the same stored decision.
- **Storage safety**: if persistence is unavailable, Lumyn returns a schema-valid `ABSTAIN` record with `STORAGE_UNAVAILABLE` (so callers can safely block write-path actions).

## Docs

- `SPECS_SCHEMAS.md`: canonical contracts + determinism rules (v0)
- `docs/quickstart.md`
- `docs/integration_checklist.md`
- `docs/architecture.md`

## Design principles

- **Decision as an artifact**: every gate yields a record.
- **Policy + outcomes, not prompts**: rules tie to action classes and objective outcomes.
- **Telemetry ≠ truth**: OpenTelemetry is for visibility; the Decision Record is the system of record.
