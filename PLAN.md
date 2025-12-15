# Lumyn MVP Execution Plan (Epics + Stories)

This plan is written to ship a “wow/aha” OSS product that technical teams can adopt on real
write-paths under incident pressure.

## Definition of Done (MVP)

- Emits `DecisionRecord` v0 for real action classes (refunds/tickets).
- Deterministic evaluation (policy + risk + memory snapshot) with golden vectors in CI.
- Local-first UX: `lumyn init` + `lumyn demo` works in minutes.
- Append-only outcomes/labels with Experience Memory similarity affecting verdicts.
- Exports Decision Records for incident review (single JSON and “decision pack” bundle).

---

## Epic 0 — Repo scaffold & dev UX (OSS-grade day 1)

### Story 0.1 — Packaging + CLI entrypoint
Paths
- `pyproject.toml`
- `src/lumyn/__init__.py`
- `src/lumyn/__main__.py`
- `src/lumyn/cli/main.py`
- `tests/test_smoke.py`

Acceptance criteria
- `uv sync --dev` works
- `uv run lumyn --help` works
- `uv run pytest` passes

Testing requirements
- CLI smoke test (Typer runner)
- import test: `python -c "import lumyn"`

### Story 0.2 — Lint/format/type gates
Paths
- `.pre-commit-config.yaml`
- `pyproject.toml` (ruff + mypy config)

Acceptance criteria
- `uv run pre-commit run --all-files` is clean
- `uv run ruff format .` + `uv run ruff check .` enforced
- `uv run mypy src` passes baseline

Testing requirements
- CI runs ruff + mypy

### Story 0.3 — CI
Paths
- `.github/workflows/ci.yml`

Acceptance criteria
- PR gates: lint, typecheck, unit tests, vectors
- Python matrix: 3.11–3.13

Testing requirements
- `pytest` + vector harness

---

## Epic 1 — Contracts: schemas + golden vectors (spec enforcement)

### Story 1.1 — Ship canonical schemas v0
Paths
- `schemas/decision_request.v0.schema.json`
- `schemas/decision_record.v0.schema.json`
- `schemas/policy.v0.schema.json`
- `schemas/reason_codes.v0.json`

Acceptance criteria
- Schemas validate example payloads
- Schema evolution rules documented (additive-only for v0)

Testing requirements
- unit tests validate schema against `examples/` and `vectors/`

### Story 1.2 — Golden vectors pack (determinism spec)
Paths
- `vectors/v0/**`
- `tests/vectors/test_vectors_v0.py`

Acceptance criteria
- 20+ vectors cover: trust, query missing evidence, escalate thresholds, abstain hard blocks, memory similarity effect
- Normalized output comparison ignores `decision_id` and `created_at`

Testing requirements
- CI fails on any verdict/reason_code drift

---

## Epic 2 — Policy spec v0 + compiler

### Story 2.1 — Policy YAML v0 + validator
Paths
- `src/lumyn/policy/spec.py`
- `src/lumyn/policy/loader.py`
- `src/lumyn/policy/validate.py`
- `policies/lumyn-support.v0.yml`

Acceptance criteria
- Policy loads, validates, computes stable `policy_hash`
- Validation catches unknown operators/reason codes

Testing requirements
- policy hash stability test (whitespace changes do not alter hash)

### Story 2.2 — Deterministic evaluator semantics
Paths
- `src/lumyn/engine/evaluator.py`
- `src/lumyn/engine/normalize.py`

Acceptance criteria
- Fixed stage order + fixed verdict precedence (as in `SPECS_SCHEMAS.md`)
- Deterministic ordering of `matched_rules` and `reason_codes`

Testing requirements
- unit tests for precedence and evaluation order
- vectors cover each stage

---

## Epic 3 — Experience Memory (MVP) + similarity

### Story 3.1 — Memory store (SQLite)
Paths
- `src/lumyn/store/sqlite.py`
- `src/lumyn/store/schema.sql`

Acceptance criteria
- Stores decisions, memory items, and decision events
- Durable persistence; if storage unavailable ⇒ `ABSTAIN` with `STORAGE_UNAVAILABLE`

Testing requirements
- sqlite integration tests

### Story 3.2 — Deterministic similarity baseline
Paths
- `src/lumyn/engine/similarity.py`

Acceptance criteria
- Similarity returns stable top-k with deterministic tie-breakers
- `failure_similarity` influences verdict through policy thresholds

Testing requirements
- unit tests for stable ordering and scoring
- vectors demonstrate compounding behavior after labeling a failure

---

## Epic 4 — Core decide() API + record emission

### Story 4.1 — Library API
Paths
- `src/lumyn/core/decide.py`
- `src/lumyn/core/records.py`

Acceptance criteria
- `decide(request) -> DecisionRecord` produces a schema-valid record and persists it
- Computes `inputs_digest`, includes `policy_hash`, includes `context.digest`

Testing requirements
- schema validation tests
- vectors harness passes

---

## Epic 5 — PLG-grade CLI

### Story 5.1 — Golden path commands
Paths
- `src/lumyn/cli/main.py`
- `src/lumyn/cli/commands/{init,demo,decide,show,explain,export,label,policy,doctor}.py`

Acceptance criteria
- `lumyn init` creates local workspace (`.lumyn/`) with sqlite + starter policy
- `lumyn demo` emits multiple real-looking Decision Records
- `lumyn label` appends events and updates memory store

Testing requirements
- CLI tests for each command (Typer runner)

---

## Epic 6 —  service mode (FastAPI)

### Story 6.1 — HTTP API wrapper
Paths
- `src/lumyn/api/app.py`
- `src/lumyn/api/routes_v0.py`

Acceptance criteria
- `POST /v0/decide` persists before returning 200
- `GET /v0/decisions/{decision_id}`
- `POST /v0/decisions/{decision_id}/events`

Testing requirements
- integration tests against FastAPI test client

---

## Epic 7 — OSS maturity (release discipline)

### Story 7.1 — OSS hygiene pack
Paths
- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `.github/ISSUE_TEMPLATE/**`

Acceptance criteria
- Clear contributor path and security reporting guidance

Testing requirements
- CI includes dependency scanning (optional)

---

## Epic 8 — Config, privacy, and service hardening

### Story 8.1 — Config file + env overrides
Paths
- `src/lumyn/config.py`
- `src/lumyn/config_default.toml` (or similar)

Acceptance criteria
- Single config file supports: storage URL, policy path, mode (enforce/advisory), redaction profile
- Environment variables override config deterministically

Testing requirements
- unit tests for precedence (env overrides file)

### Story 8.2 — Redaction profiles (digest-only default)
Paths
- `src/lumyn/engine/redaction.py`

Acceptance criteria
- Default behavior stores digest-only safely
- Inline context can be redacted before persistence with deterministic “fields_removed” output

Testing requirements
- unit tests for redaction determinism

### Story 8.3 — Request signing (service mode)
Paths
- `src/lumyn/api/auth.py`

Acceptance criteria
- Optional shared-secret HMAC signing for `POST /v0/decide`
- Clear error reason code on auth failure (no 500s)

Testing requirements
- API tests for signed and unsigned modes

---

## Epic 9 — Observability and performance baselines

### Story 9.1 — Structured logs and OpenTelemetry
Paths
- `src/lumyn/telemetry/logging.py`
- `src/lumyn/telemetry/tracing.py`

Acceptance criteria
- Logs include `decision_id`, `policy_hash`, and verdict
- OTel spans are optional; never replace the Decision Record as record-of-truth

Testing requirements
- smoke tests ensure logging doesn’t leak secrets

### Story 9.2 — Performance baselines
Paths
- `benchmarks/`
- `tests/perf/test_decide_p95.py` (lightweight, optional in CI)

Acceptance criteria
- Establish a repeatable local benchmark command for `decide()`
- Track regressions over time (documented thresholds)

Testing requirements
- perf tests run optionally (nightly or manual), not blocking PRs initially

---

## Epic 10 — Releases and adoption loops

### Story 10.1 — Release automation
Paths
- `.github/workflows/release.yml`
- `CHANGELOG.md`

Acceptance criteria
- Tagged releases build and publish artifacts (wheel/sdist)
- Release notes link to schema/policy changes

Testing requirements
- release workflow runs build checks

### Story 10.2 — Adoption-grade docs and examples
Paths
- `docs/quickstart.md`
- `examples/curl/*.json`
- `examples/python/*.py`

Acceptance criteria
- “15 minutes to first Decision Record” is copy/paste-able
- Examples mirror real support/refund workflows

Testing requirements
- schema validation for example payloads
