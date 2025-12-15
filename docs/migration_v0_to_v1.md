## Migration: v0 → v1 (preview)

Lumyn `v0` is the current stable contract. `v1` in this repo is a **preview** of a future stable
API/contract. This guide explains what changes, what stays stable, and how to migrate artifacts.

## What changes in v1

- Verdict model becomes the four-outcome operator model:
  - `ALLOW | DENY | ABSTAIN | ESCALATE`
- Schemas exist as new contracts:
  - `decision_request.v1`
  - `decision_record.v1`
  - `policy.v1` (not yet the default starter policy)

## v0 → v1 mapping rules (today)

When converting stored artifacts, Lumyn uses these rules:

- `TRUST` → `ALLOW`
- `ESCALATE` → `ESCALATE`
- `ABSTAIN` → `ABSTAIN`
- `QUERY` → `DENY` (deny-until-evidence; `DecisionRecord.queries` remains the source of required fields)

## Convert a DecisionRecord JSON

Convert a stored record export:

`lumyn convert decision_record.json --to v1 --out decision_record.v1.json`

## Convert a decision pack ZIP

Convert an exported decision pack:

`lumyn convert decision_pack.zip --to v1 --out decision_pack_v1.zip`

## Replay a v1 pack

`lumyn replay` accepts both v0 and v1 packs:

`lumyn replay decision_pack_v1.zip`

### Digest note (v1 preview)

In the current preview, `/v1/decide` is implemented as a wrapper around the v0 engine.
`determinism.inputs_digest` is therefore computed using the v0-equivalent request (the same request
with `schema_version` treated as `decision_request.v0`).

This makes v0→v1 converted packs replayable without changing the underlying decision semantics.
