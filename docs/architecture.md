# Architecture

This document describes Lumyn’s current (v0) architecture as implemented in this repo: a Python SDK, a PLG-grade CLI, and an optional FastAPI service that all produce the same `DecisionRecord` contract.

## High-level component architecture

```mermaid
flowchart TB
  subgraph Caller["Your App / Agent System"]
    SDK["Python SDK\n`lumyn.core.decide.decide()`"]
    CLI["CLI\n`lumyn.cli.main` (Typer)"]
    SVCClient["Service client\nHTTP `POST /v0/decide`"]
  end

  subgraph Lumyn["Lumyn (this repo)"]
    Policy["Policy\nYAML `policy.v0`\n`lumyn.policy.loader` + `lumyn.policy.validate`"]
    Schemas["Schemas\nJSON Schema v0\n`schemas/*.json`"]
    Engine["Engine\nnormalize + evaluate\n`lumyn.engine.*`"]
    Similarity["Experience Memory similarity\n`lumyn.engine.similarity`"]
    Records["Record emission\n`lumyn.records.emit`"]
    Store["SQLite store\n`lumyn.store.sqlite` + `src/lumyn/store/schema.sql`"]
    Service["FastAPI service\n`lumyn.api.app:create_app`\n`lumyn.api.routes_v0`"]
    Auth["Optional signing\n`lumyn.api.auth`"]
    Export["Decision pack export\n`lumyn.cli.commands.export`"]
    Replay["Pack replay/verify\n`lumyn.cli.commands.replay`"]
    Telemetry["Telemetry\n`lumyn.telemetry.logging` + `lumyn.telemetry.tracing`"]
  end

  subgraph Artifacts["Artifacts (incident-grade)"]
    DecisionRecord["DecisionRecord JSON\n`decision_record.v0`"]
    DecisionPack["Decision pack ZIP\n(record + request + policy snapshot)"]
  end

  Caller --> SDK
  Caller --> CLI
  Caller --> SVCClient

  SDK --> Schemas
  SDK --> Policy
  SDK --> Engine
  SDK --> Similarity
  SDK --> Records
  SDK --> Store
  SDK --> Telemetry
  SDK --> DecisionRecord

  CLI --> SDK
  CLI --> Export
  CLI --> Replay
  Export --> Store
  Export --> Schemas
  Export --> DecisionPack
  Replay --> Schemas
  Replay --> DecisionPack

  SVCClient --> Service
  Service --> Auth
  Service --> SDK
  Service --> DecisionRecord
```

## SDK flow: `decide()` end-to-end

The SDK is the source-of-truth flow; both the CLI and the service call into it.

```mermaid
sequenceDiagram
  autonumber
  participant App as Your app
  participant Decide as lumyn.core.decide.decide()
  participant Schema as schemas/decision_request.v0.schema.json
  participant Policy as lumyn.policy.loader.load_policy()
  participant Normalize as lumyn.engine.normalize.normalize_request()
  participant Store as lumyn.store.sqlite.SqliteStore
  participant Similarity as lumyn.engine.similarity.top_k_matches()
  participant Eval as lumyn.engine.evaluator.evaluate_policy()
  participant Redact as lumyn.engine.redaction.redact_request_for_persistence()
  participant Emit as lumyn.records.emit.build_decision_record()
  participant Log as lumyn.telemetry.logging.log_decision_record()

  App->>Decide: DecisionRequest (dict)
  Decide->>Schema: validate request
  Decide->>Policy: load + validate + policy_hash
  Decide->>Normalize: derive amount_usd, evidence view, action_type
  Decide->>Store: init() + put_policy_snapshot()
  Decide->>Store: list_memory_items(tenant_id, action_type)
  Decide->>Similarity: compute failure similarity score/top_k
  Decide->>Decide: inject evidence.failure_similarity_score
  Decide->>Eval: evaluate policy stages (deterministic)
  Decide->>Redact: redact request for persistence (digest-only safe defaults)
  Decide->>Emit: build DecisionRecord v0
  Decide->>Store: put_decision_record(record)
  Decide->>Log: log safe summary (JSON)
  Decide-->>App: DecisionRecord (dict)
```

### Failure semantics: storage unavailable

If SQLite persistence is unavailable, Lumyn returns a schema-valid `DecisionRecord` with:
- `verdict=ABSTAIN`
- `reason_codes` includes `STORAGE_UNAVAILABLE`

This applies to SDK and service mode (service should return 200 with an ABSTAIN record, not 500).

## CLI flows (PLG paths)

```mermaid
flowchart TD
  subgraph CLI["CLI entrypoints (`lumyn ...`)"]
    Init["init\n`lumyn.cli.commands.init`"]
    Demo["demo / demo --story\n`lumyn.cli.commands.demo`"]
    DecideCmd["decide\n`lumyn.cli.commands.decide`"]
    Label["label\n`lumyn.cli.commands.label`"]
    Export["export --pack\n`lumyn.cli.commands.export`"]
    Replay["replay\n`lumyn.cli.commands.replay`"]
    Doctor["doctor / doctor --fix\n`lumyn.cli.commands.doctor`"]
    Serve["serve / serve --dry-run\n`lumyn.cli.commands.serve`"]
  end

  Workspace["Workspace\n`.lumyn/`\n- policy.yml\n- lumyn.db"]:::artifact
  SDK["SDK\n`lumyn.core.decide.decide()`"]:::core
  Pack["decision_pack.zip"]:::artifact

  Init --> Workspace
  Doctor --> Workspace
  Demo --> SDK
  DecideCmd --> SDK
  Label --> Workspace
  Export --> Workspace --> Pack
  Replay --> Pack
  Serve --> SDK

  classDef artifact fill:#f6f8fa,stroke:#6b7280,color:#111827;
  classDef core fill:#eef2ff,stroke:#4f46e5,color:#111827;
```

## Service flow: FastAPI `POST /v0/decide`

The service is a thin HTTP wrapper around the SDK.

```mermaid
sequenceDiagram
  autonumber
  participant Client as HTTP client
  participant API as lumyn.api.routes_v0
  participant Auth as lumyn.api.auth (optional)
  participant SDK as lumyn.core.decide.decide()
  participant Store as lumyn.store.sqlite.SqliteStore

  Client->>API: POST /v0/decide (raw JSON body)
  API->>Auth: verify X-Lumyn-Signature (optional)
  API->>SDK: decide(request)
  SDK->>Store: persist DecisionRecord (or ABSTAIN on storage failure)
  SDK-->>API: DecisionRecord
  API-->>Client: 200 DecisionRecord JSON
```

## Incident flow: decision pack export and replay verify

Decision packs are designed to be copied into incident tickets and validated offline.

```mermaid
sequenceDiagram
  autonumber
  participant Oncall as On-call engineer
  participant Export as lumyn export --pack
  participant Store as lumyn.store.sqlite.SqliteStore
  participant Pack as decision_pack.zip
  participant Replay as lumyn replay
  participant Schemas as schemas/*.json

  Oncall->>Export: lumyn export <decision_id> --pack
  Export->>Store: get_decision_record(decision_id)
  Export->>Store: get_policy_snapshot(policy_hash)
  Export-->>Pack: write ZIP (record + request + policy + digests)
  Oncall->>Replay: lumyn replay decision_pack.zip
  Replay->>Pack: read record/request/policy
  Replay->>Schemas: validate against v0 schemas
  Replay-->>Oncall: exit 0 + deterministic summary
```

## Key “source of truth” files

- SDK core: `src/lumyn/core/decide.py`
- Policy: `src/lumyn/policy/loader.py`, `src/lumyn/policy/validate.py`, `policies/*.yml`
- Engine: `src/lumyn/engine/evaluator.py`, `src/lumyn/engine/normalize.py`, `src/lumyn/engine/similarity.py`
- Records: `src/lumyn/records/emit.py`, `schemas/decision_record.v0.schema.json`
- Store: `src/lumyn/store/sqlite.py`, `src/lumyn/store/schema.sql`
- Service: `src/lumyn/api/app.py`, `src/lumyn/api/routes_v0.py`, `src/lumyn/api/auth.py`
- CLI: `src/lumyn/cli/main.py`, `src/lumyn/cli/commands/*`
