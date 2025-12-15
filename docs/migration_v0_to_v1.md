# Migration: v0 → v1

Lumyn `v1` is the current stable contract. `v0` is legacy/deprecated.

## Major Changes
- **Verdicts**: `TRUST` removed (use `ALLOW`). `QUERY` removed (use `DENY` or `ABSTAIN` depending on intent).
- **Digests**: `inputs_digest` calculation changed to be more robust.
- **Strictness**: `policy.v1` validation fails if you use unknown keys.

## Migration Guide

### 1. Migrate Policy
Run the automated migration tool:

`lumyn migrate policies/my-legacy.v0.yml --out policies/my-policy.v1.yml`

This will:
- Rename actions/verdicts (TRUST -> ALLOW).
- Check for unsupported keys.
- Update schema version.

### 2. Update Application Code
Change your JSON request generation:
- Set `schema_version` to `decision_request.v1`.
- Update your verdict handling logic (`if verdict == "ALLOW": ...`).

### 3. Verify
Run `lumyn policy validate --workspace .` to ensure the new policy is strictly valid.
