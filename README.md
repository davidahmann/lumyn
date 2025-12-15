# Lumyn

**Decision Records for production AI.**

Lumyn is a deterministic `decide()` gateway for AI systems that take real actions (refunds,
ticket operations, account changes). Instead of “the model said so,” Lumyn returns a
verdict — `TRUST | ABSTAIN | ESCALATE | QUERY` — and writes a durable **Decision Record**
you can replay during incidents.

## Why teams adopt Lumyn

- **Write-path safety**: gates consequential actions with explicit policy and outcomes.
- **Replayable decisions**: stable digests (`policy.policy_hash`, `request.context.digest`, `determinism.inputs_digest`).
- **No bluffing**: uncertainty becomes `ABSTAIN`, `ESCALATE`, or `QUERY` with reason codes.
- **Compounding reliability**: labeled failures/successes feed Experience Memory similarity.
- **Drop-in**: works as a Python library and as an optional HTTP service.

## The primitive

You wrap a risky action with `decide()`:

1) you provide a `DecisionRequest` (subject, action, evidence, `context.digest`)
2) Lumyn evaluates deterministic policy + risk signals + experience similarity
3) Lumyn returns a `DecisionRecord` and persists it (append-only)

The Decision Record is the unit you export into incidents, tickets, and postmortems.

## What a Decision Record looks like

```json
{
  "schema_version": "decision_record.v0",
  "decision_id": "dec_01JZ1S7Y1NQ2A0D5JQK2Q2P3X4",
  "created_at": "2026-01-13T14:12:05Z",
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

## Quickstart (intended)

The MVP ships as:
- a Python package + CLI (`lumyn`)
- an optional local service (`POST /v0/decide`)

Install (once published to PyPI):
- `pip install lumyn`

Key CLI workflows:
- `lumyn init` (creates local SQLite + starter policy)
- `lumyn demo` (emits a few real-looking Decision Records as JSON)
- `lumyn decide --in request.json` (prints a Decision Record)
- `lumyn show <decision_id>`, `lumyn explain <decision_id>`, `lumyn export <decision_id>`
- `lumyn export <decision_id> --pack --out decision_pack.zip`
- `lumyn label <decision_id> --label failure --summary "Bad outcome in prod"`
- `lumyn policy validate` (validates `.lumyn/policy.yml`) or `lumyn policy validate --path ./policy.yml`
- `lumyn doctor` (workspace health + counts)

Service mode (FastAPI):
- `uv run python -c "from lumyn.api.app import create_app; app = create_app(); print(app)"` (sanity)
- Run with Uvicorn: `uv run uvicorn --factory lumyn.api.app:create_app --host 127.0.0.1 --port 8000`
- Env config: `LUMYN_POLICY_PATH`, `LUMYN_STORAGE_URL` (e.g. `sqlite:.lumyn/lumyn.db`), `LUMYN_MODE`, `LUMYN_REDACTION_PROFILE`, `LUMYN_SIGNING_SECRET`
- If `LUMYN_SIGNING_SECRET` is set, `POST /v0/decide` requires `X-Lumyn-Signature: sha256:<hmac(body)>` over the exact request body bytes.
- `GET /v0/policy` returns `{policy_id, policy_version, policy_hash}` for the currently loaded policy.

Docs:
- `docs/quickstart.md`

## Documentation

- `PRD.md`: what we’re building, for whom, and why
- `SPECS_SCHEMAS.md`: canonical contracts + determinism rules (v0)
- `PLAN.md`: epics/stories with acceptance criteria and tests
- `REPO_STRUCTURE.md`: proposed OSS layout

## Design principles

- **Decision as an artifact**: every gate yields a record.
- **Policy + outcomes, not prompts**: rules tie to action classes and objective outcomes.
- **Telemetry ≠ truth**: OpenTelemetry is for visibility; the Decision Record is the system of record.
