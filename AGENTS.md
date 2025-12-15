# AGENTS.md (Repository Instructions)

This file exists to help automated coding agents (and humans) work effectively in this repo.
Agentic tools read `AGENTS.md` to learn repo conventions, how to run checks/tests, and what
contracts must not drift. Nested `AGENTS.md` files (in subdirectories) override this one
for files within their subtree.

## Product North Star

Lumyn is a deterministic **decision gateway** for production AI: every gated action emits a
durable **Decision Record** with a verdict (`ALLOW | ABSTAIN | ESCALATE | DENY`), stable
reason codes, and replayable digests. "Decisions you can't replay aren't decisions."

## Repo Invariants (Do Not Break)

- **Contracts-first**: `decision_request.v1` and `decision_record.v1` are versioned public
  contracts. Breaking changes require a new major schema (e.g. `*.v2`), not edits to v1.
- **Determinism**: identical inputs + policy + memory snapshot must yield identical normalized
  outputs (excluding `decision_id` and `created_at`).
- **Reason codes are a contract**: reason codes are stable machine strings (no dynamic content).
- **Append-only records**: outcomes/labels/overrides are appended as events; do not silently
  mutate a prior decision record.
- **Strict v1 Engine**: The engine must strictly validate `policy.v1` keys. No unknown keys allowed.

## Development Tooling (Target)

The implementation plan assumes:
- Python **3.11+** (recommended: 3.12/3.13), managed with `uv`
- Formatting/lint: `ruff`
- Type-checking: `mypy`
- Tests: `pytest` (+ golden vectors in `vectors/v1/`)

When code exists, keep these commands working:
- `uv sync --dev`
- `uv run ruff format . && uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

## Canonical Docs (Authoritative)

- `README.md`: product surface + quickstart expectations (v1-first)
- `PRD.md`: goals, non-goals, requirements
- `SPECS_SCHEMAS.md`: contracts, semantics, hashing/determinism rules
- `PLAN.md`: epics/stories + acceptance + tests
- `REPO_STRUCTURE.md`: intended OSS repo layout
