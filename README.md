# Lumyn

**Decision Records for production AI.**

Lumyn is a deterministic `decide()` gateway for AI agents. It enforces strict policies, returns explicit verdicts (`ALLOW`, `DENY`, `ESCALATE`, `ABSTAIN`), and writes durable **Decision Records** for instant incident replay.

With **Lumyn Memory**, it learns from verified outcomes to block repeated failures ("Pre-Cognition") and fast-track proven successes ("Self-Healing").

> [!NOTE]
> **v1.0.0 Stable**: This documentation covers the v1 engine. For legacy v0 documentation, see [Legacy Specs](SPECS_SCHEMAS.md#legacy-specs-v0).

## When an AI incident happens

Support shares a screenshot.
Engineering tries to reconstruct what the model saw and what policy/risk rules fired.
Nobody can answer, precisely and repeatably: what happened, what changed, and why did we allow it?

Lumyn's unit of evidence is a `decision_id`. Paste it into the ticket, then:

- `lumyn show <decision_id>`
- `lumyn explain <decision_id> --markdown`
- `lumyn export <decision_id> --pack --out decision_pack.zip`
- `lumyn replay decision_pack.zip --markdown`

## Why teams adopt Lumyn

- **Write-path safety**: gates consequential actions with explicit policy and outcomes.
- **Replayable decisions**: stable digests (`policy.policy_hash`, `request.context.digest`, `determinism.inputs_digest`).
- **No bluffing**: uncertainty becomes `ABSTAIN` or `ESCALATE` with reason codes.
- **Compounding reliability**: labeled failures/successes feed Experience Memory similarity.
- **Drop-in**: works as a Python library and as an optional HTTP service.

## Operations & Safety

#### 📺 The War Room (`lumyn monitor`)
"Less drama. Fewer incidents."
A live, scrolling Matrix-style TUI showing decisions as they happen.
```bash
lumyn monitor --limit 50
```

#### 🛡️ Regression Testing (`lumyn diff`)
"Did my change block valid users?"
Run a candidate policy against a history of past records to catch regressions before deployment.
```bash
lumyn diff past_traffic.json --policy new_policy.v1.yml
```

## The primitive

You wrap a risky action with `decide()`:

1) you provide a `DecisionRequest` (subject, action, evidence, `schema_version: decision_request.v1`)
2) Lumyn evaluates deterministic `policy.v1` (strict stages + conditions)
3) Lumyn returns a `DecisionRecord` and persists it (append-only)

The Decision Record is the unit you export into incidents, tickets, and postmortems.

## How it works (one screen)

- You provide a `DecisionRequest` (no external fetches in v1; your app supplies `evidence`).
- Lumyn evaluations occur in 5 strict stages: `REQUIREMENTS` -> `HARD_BLOCKS` -> `ESCALATIONS` -> `ALLOW_PATHS` -> `DEFAULT`.
- Lumyn computes Experience Memory similarity from prior labeled outcomes.
- Lumyn persists the Decision Record to SQLite before returning (or returns ABSTAIN on storage failure).

## What a Decision Record looks like

```json
{
  "schema_version": "decision_record.v1",
  "decision_id": "01JZ1S7Y1NQ2A0D5JQK2Q2P3X4",
  "created_at": "2025-12-15T10:00:00Z",
  "request": {
    "schema_version": "decision_request.v1",
    "subject": { "type": "service", "id": "support-agent", "tenant_id": "acme" },
    "action": {
      "type": "support.refund",
      "intent": "Refund duplicate charge for order 82731",
      "amount": { "value": 201.0, "currency": "USD" }
    },
    "evidence": { "ticket_id": "ZD-1001", "order_id": "82731", "payment_instrument_risk": "low" },
    "context": { "mode": "digest_only", "digest": "sha256:aaaaaaaa..." }
  },
  "policy": {
    "policy_id": "lumyn-support",
    "policy_version": "1.0.0",
    "policy_hash": "sha256:bbbbbb...",
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
    "engine_version": "1.0.0",
    "inputs_digest": "sha256:cccc..."
  }
}
```

## Quickstart (no keys, no Docker)

Install:
- `pip install lumyn`
- Service mode: `pip install lumyn[service]`

Fastest "aha" (compounding in seconds):

- `lumyn doctor --fix`
- `lumyn demo --story`

Common CLI workflows:
- `lumyn init` (creates local SQLite + starter policy)
- `lumyn monitor` (watch decisions live)

Key capabilities:
- **Policy-as-Code** (YAML)
- **Institutional Memory** (Learn from outcomes)
- **GitOps-native** workflow
- **Local & Fast** (SQLite + deterministic engine)

## Quickstart

### 1. Initialize
```bash
uv tool install lumyn
lumyn init
```

### 2. Make a Decision
```bash
lumyn decide request.json
```

### 3. Teach (Optional)
```bash
# If a decision turns out to be bad (e.g. fraud), teach Lumyn:
lumyn learn <decision_id> --outcome FAILURE
```
- `lumyn show <decision_id>`, `lumyn explain <decision_id>`
- `lumyn export <decision_id> --pack --out decision_pack.zip`
- `lumyn replay decision_pack.zip` (validate pack + digests)
- `lumyn policy validate` (strict v1 validation)
- `lumyn migrate old_policy.v0.yml` (upgrade to v1)

## SDK (drop-in)

Lumyn does not call your model. You call Lumyn before (or around) a real write-path action.

```python
from lumyn import LumynConfig, decide_v1

cfg = LumynConfig(
    policy_path="policies/starter.v1.yml",  # built-in starter policy (v1)
    store_path=".lumyn/lumyn.db",
)

record = decide_v1(
    {
        "schema_version": "decision_request.v1",
        "request_id": "req_123", # recommended for retries
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {
            "type": "support.refund",
            "intent": "Refund duplicate charge",
            "amount": {"value": 20.0, "currency": "USD"},
        },
        "evidence": {
            "ticket_id": "ZD-1001",
            "order_id": "82731",
            "customer_id": "C-9",
            "payment_instrument_risk": "low",
            "chargeback_risk": 0.05,
            "previous_refund_count_90d": 0,
            "customer_age_days": 180,
        },
        "context": {
            "mode": "digest_only",
            "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000"
        }
    },
    config=cfg,
)

if record["verdict"] == "ALLOW":
    pass  # perform the write-path action
elif record["verdict"] == "ESCALATE":
    pass  # route to human queue
else:
    pass  # block (ABSTAIN/DENY)
```

## Service mode (FastAPI)

Run:
- `lumyn serve`

Call:

`curl -sS -X POST http://127.0.0.1:8000/v1/decide -H 'content-type: application/json' --data-binary @request.json`

Endpoints:
- `POST /v1/decide` -> DecisionRecord (v1)
- `GET /v1/decisions/{decision_id}`
- `GET /v1/policy`

## Documentation

- [Feature Overview & Quickstart](docs/quickstart.md)
- [v1 Semantics Reference](docs/v1_semantics.md)
- [Lumyn Memory & Learning](docs/memory.md)
- [Architecture](docs/architecture.md)
- [Specs & Schemas](SPECS_SCHEMAS.md)
- [Integration Checklist](docs/integration_checklist.md)
- [Migration Guide](docs/migration_v0_to_v1.md)

## Design principles

- **Decision as an artifact**: every gate yields a record.
- **Policy + outcomes, not prompts**: rules tie to action classes and objective outcomes.
- **Telemetry ≠ truth**: OpenTelemetry is for visibility; the Decision Record is the system of record.

---

<p align="center">
  <a href="https://lumynoss.vercel.app"><strong>Try in Browser</strong></a> ·
  <a href="https://davidahmann.github.io/lumyn/docs/quickstart"><strong>Quickstart</strong></a> ·
  <a href="https://davidahmann.github.io/lumyn/docs/"><strong>Docs</strong></a>
</p>
