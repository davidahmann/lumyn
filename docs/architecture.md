# Architecture

This document describes Lumyn’s architecture: a Python SDK, a CLI, and an optional FastAPI service that all produce deterministic `DecisionRecord` artifacts.

## High-level component architecture

```mermaid
flowchart TB
  subgraph Caller["Your App / Agent System"]
    SDK["Python SDK\n`lumyn.core.decide`"]
    CLI["CLI\n`lumyn.cli.main`"]
    SVCClient["Service client\nHTTP `POST /v1/decide`"]
  end

  subgraph Lumyn["Lumyn (this repo)"]
    Policy["Policy\n`lumyn.policy.loader`\n`policies/starter.v1.yml`"]
    Schemas["Schemas\nJSON Schema v0 & v1\n`schemas/*.json`"]
    Engine["Engine\nnormalize + evaluate\n`lumyn.engine.evaluator_v1`"]
    Similarity["Experience Memory similarity\n`lumyn.engine.similarity`"]
    Records["Record emission\n`lumyn.records`"]
    Store["SQLite store\n`lumyn.store.sqlite`"]
    Service["FastAPI service\n`lumyn.api.app`"]
    Auth["Optional signing\n`lumyn.api.auth`"]
    Export["Decision pack export\n`lumyn.cli.commands.export`"]
    Replay["Pack replay/verify\n`lumyn.cli.commands.replay`"]
  end

  subgraph Artifacts["Artifacts (incident-grade)"]
    DecisionRecord["DecisionRecord JSON\n`decision_record.v1`"]
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
  SDK --> DecisionRecord

  CLI --> SDK
  CLI --> Export
  CLI --> Replay
  Export --> Store
  Export --> DecisionPack
  Replay --> DecisionPack

  SVCClient --> Service
  Service --> SDK
  Service --> DecisionRecord
```

## SDK flow: `decide_v1()` end-to-end

The SDK is the source-of-truth flow; both the CLI and the service call into it.

```mermaid
sequenceDiagram
  autonumber
  participant App as Your app
  participant Decide as lumyn.core.decide.decide_v1()
  participant Schema as schemas/decision_request.v1.schema.json
  participant Policy as lumyn.policy.loader
  participant Normalize as lumyn.engine.normalize_v1
  participant Store as lumyn.store.sqlite.SqliteStore
  participant Eval as lumyn.engine.evaluator_v1
  participant Emit as lumyn.records.emit_v1

  App->>Decide: DecisionRequest (dict)
  Decide->>Schema: validate request
  Decide->>Policy: load + validate_v1
  Decide->>Normalize: derive features + inputs_digest_v1
  Decide->>Store: init() + put_policy_snapshot()
  Decide->>Eval: evaluate policy (5 stages)
  Decide->>Emit: build DecisionRecord v1
  Decide->>Store: put_decision_record(record)
  Decide-->>App: DecisionRecord (dict)
```

## CLI flows

```mermaid
flowchart TD
  subgraph CLI["CLI entrypoints (`lumyn ...`)"]
    Init["init\n(v1 default)"]
    Demo["demo / demo --story"]
    DecideCmd["decide"]
    Export["export --pack"]
    Replay["replay"]
    Serve["serve"]
  end

  Workspace["Workspace\n`.lumyn/`\n- policy.yml\n- lumyn.db"]:::artifact
  SDK["SDK"]:::core
  Pack["decision_pack.zip"]:::artifact

  Init --> Workspace
  Demo --> SDK
  DecideCmd --> SDK
  Export --> Workspace --> Pack
  Replay --> Pack
  Serve --> SDK

  classDef artifact fill:#f6f8fa,stroke:#6b7280,color:#111827;
  classDef core fill:#eef2ff,stroke:#4f46e5,color:#111827;
```

## Key "source of truth" files

- SDK core: `src/lumyn/core/decide.py`
- Policy V1: `src/lumyn/policy/validate.py` (strict validation logic)
- Engine V1: `src/lumyn/engine/evaluator_v1.py`
- Records: `src/lumyn/records/emit_v1.py`
- Service: `src/lumyn/api/routes_v1.py`
