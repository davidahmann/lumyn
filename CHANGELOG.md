# Changelog

All notable changes to this project will be documented in this file.

This project follows SemVer. Schema changes are tracked explicitly; v0 schemas are additive-only.

## Unreleased

### Schemas / Contracts
- No changes.

### Policy
- No changes.

### Engine / SDK / CLI / Service
- No changes.

## 0.1.0

First OSS release.

### Schemas / Contracts
- Shipped v0 schemas for DecisionRequest/DecisionRecord/Policy and stable reason codes.

### Engine / SDK / CLI / Service
- Deterministic policy evaluator with golden vectors.
- Local-first SQLite persistence (persist-before-return) plus append-only events and Experience Memory.
- PLG CLI: `init`, `demo`, `decide`, `show`, `explain`, `export` (JSON + `--pack`), `label`, `policy validate`, `doctor`.
- Optional FastAPI service: `POST /v0/decide`, `GET /v0/decisions/{decision_id}`, `POST /v0/decisions/{decision_id}/events`, `GET /v0/policy`.
- Optional HMAC request signing for service mode (`LUMYN_SIGNING_SECRET`).
