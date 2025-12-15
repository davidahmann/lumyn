# Lumyn — MVP PRD (OSS + PLG)

## One-liner

Lumyn is a **decision gateway for production AI**. It turns “the model said so” into a
deterministic **Decision Record**: a verdict (`TRUST | ABSTAIN | ESCALATE | QUERY`), stable
reason codes, and replayable digests that hold up during incidents.

## Problem

Teams are shipping LLM apps and agents that take real actions (refunds, ticket changes,
account updates, customer comms). When something goes wrong, they need answers that prompts
and logs can’t reliably provide:

- Why did it do that?
- Should it have been allowed?
- What would have prevented it?
- How do we stop it happening again?

Lumyn supplies the missing primitive: a deterministic `decide()` gate that produces a
replayable record-of-truth for every action.

## Target wedge (MVP)

Beachhead: **AI-powered support ops automation**
- refunds/credits
- ticket close/update/reopen
- customer messages
- account lock/unlock

Why: high volume, clear blast radius, obvious incident pressure, strong appetite for
abstain/escalate gates.

## ICP

- 50–2,000 employees (or a high-agency team inside enterprise)
- shipping AI automation into production now
- Python/TypeScript backends, orchestrator or custom pipelines
- has policy/guardrails scattered across prompts and if-statements, but no unified decision record

## Personas

- AI Platform Engineer (primary): standard interface, deterministic gates, low overhead, easy rollback
- Backend/Staff Engineer owning workflow (primary): fewer incidents, reproducible decisions, clear “why”
- Support Ops/Product Ops Lead (secondary): safe automation that knows when to stop
- Security/Compliance (future): artifacts and controls (later: proof/attestation integration)

## JTBD

When my AI system is about to take a consequential action,
I want a deterministic gate that can trust/abstain/escalate/query and leave a durable record,
so incidents drop, accountability is clear, and failures teach the system instead of repeating.

## Goals (MVP)

- Make decisions explicit: every gated action emits a Decision Record.
- Make risk compounding: labeled outcomes feed Experience Memory similarity.
- Be drop-in: library and optional service; no dependency on other systems.
- Be OSS/PLG: install in minutes; obvious value day 1.
- Be incident-grade: deterministic behavior and replayable digests.

## Non-goals (MVP)

- Training/fine-tuning backbone models as a product feature.
- Full compliance attestations or cryptographic proofs (design for later integration).
- Building a full UI suite (CLI-first; minimal web later if needed).
- Owning the agent runtime (Lumyn is a gate + record + memory, not an orchestrator).

## Functional requirements

FR1 — Decide API
- Input: `DecisionRequest` v0
- Output: `DecisionRecord` v0
- Deterministic given same inputs + policy + memory snapshot

FR2 — Policy definition and versioning
- Policy expressed in YAML (policy v0 spec)
- `policy_hash` included in every Decision Record
- Hot reload (service mode) or explicit reload (library mode)

FR3 — Experience Memory store
- Default: SQLite (local-first)
- Optional: Postgres (shared installs)
- Supports similarity lookup and stable top-k results (deterministic tie-breaking)

FR4 — Outcome/feedback append (append-only)
- Label decisions as `failure|success|near_miss`
- Never overwrite the original decision record; append events

FR5 — CLI (PLG-grade)
- `init`, `demo`, `decide`, `show`, `explain`, `export`, `label`, `policy validate`, `doctor`
- `export` supports a “decision pack” bundle for incident workflows

FR6 — Integrations (examples, not deep productization)
- example adapter hooks for LangChain/LlamaIndex and generic “HTTP action gate”

## Non-functional requirements

- **Determinism**: normalized DecisionRecord is stable across runs.
- **Latency**: local p95 `decide()` < 25ms (excluding any external LLM calls).
- **Reliability**: no data loss for Decision Records; if persistence fails, return `ABSTAIN`.
- **Privacy**: default to `context.mode=digest_only`; support redaction for inline contexts.
- **Portability**: runs locally and in containers; minimal dependencies.

## Success criteria (90–120 days post-ship)

- Time-to-first-decision: < 15 minutes from README to first Decision Record.
- At least 3 real integrations gating consequential actions.
- Evidence of compounding: at least one case where a labeled failure changes future verdicts.
- Organic usage: >50 weekly Decision Records in at least 3 installs.

## Open questions to lock early

- Starter policy scope for v0 (which action types ship day 1).
- How to treat time-dependent signals (rate limits, drift) without breaking determinism.
- Which “decision pack” export format teams want first (single JSON vs bundle with vectors/context refs).
