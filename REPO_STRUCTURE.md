# Repository Structure (Proposed)

This repo is designed to feel **incident-grade** on day 1: contracts are top-level, golden vectors
are treated as the spec, and the CLI provides the PLG “golden path”.

## Top-level layout

```text
.
├── AGENTS.md
├── README.md
├── PRD.md
├── SPECS_SCHEMAS.md
├── PLAN.md
├── REPO_STRUCTURE.md
│
├── schemas/                          # versioned public contracts
│   ├── decision_request.v0.schema.json
│   ├── decision_record.v0.schema.json
│   ├── policy.v0.schema.json
│   └── reason_codes.v0.json          # stable catalog
│
├── policies/                         # starter policy packs (PLG onboarding)
│   ├── lumyn-support.v0.yml
│   └── packs/
│       ├── support-refunds.v0.yml
│       └── support-ticket-actions.v0.yml
│
├── vectors/                          # golden vectors = determinism spec enforcement
│   └── v0/
│       └── support/
│           ├── 001_refund_small_trust.json
│           ├── 002_refund_missing_evidence_query.json
│           └── ...
│
├── examples/                         # copy/paste integration examples
│   ├── curl/
│   └── python/
│
├── docs/                             # short, operational docs (keep minimal + practical)
│   ├── quickstart.md
│   ├── concepts/
│   └── reference/
│
├── benchmarks/                       # optional perf harness (not required for PLG)
│   └── README.md
│
├── src/
│   └── lumyn/
│       ├── __init__.py
│       ├── cli/
│       ├── api/                      # optional FastAPI surface
│       ├── engine/                   # deterministic evaluator/compiler/digests
│       ├── policy/
│       ├── store/                    # sqlite/postgres backends
│       └── telemetry/                # structured logs + optional OpenTelemetry
│
└── tests/
    ├── unit/
    ├── integration/
    └── vectors/                      # tests that execute vectors/ and assert exact outputs
```

## Why this structure

- **Contracts-first**: schemas are versioned, explicit, and easy to diff.
- **Golden vectors enforce determinism**: CI fails on contract drift.
- **Policies are product**: starter packs are the onboarding experience.
- **Surfaces share a core**: library + service mode are wrappers around the same engine.
