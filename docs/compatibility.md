# Compatibility & Deprecation Policy

Lumyn follows semantic versioning. This document outlines our guarantees for v0 (Legacy) and v1 (Stable) engines.

## Version Status

| Version | Status | Guarantee | Policy Schema | Engine URL |
| :--- | :--- | :--- | :--- | :--- |
| **v1.x** | **Stable** | Active development. No breaking changes to contracts. | `policy.v1` | `/v1/decide` |
| **v0.x** | **Deprecated (Supported)** | Security fixes & critical bug fixes only. | `policy.v0` | `/v0/decide` |

## v0 Deprecation Timeline

- **Announced**: with v1.0.0-rc.1 release.
- **End of Feature Support**: Immediate. No new features will be backported to v0.
- **End of Life (EOL)**: v2.0.0 release (estimated late 2026). Until then, v0 policies and endpoints will continue to function on the v1.x binary.

## Breaking Changes in v1

To ensure determinism and reliability, v1 introduces the following breaking changes compared to v0:
- **Strict Stages**: `policy.v1` enforces 5 specific evaluation stages.
- **Limited Operators**: Arbitrary condition keys are no longer allowed; only supported operators (e.g., `_gt`, `_is`) work.
- **Verdict Precedence**: `ABSTAIN` (System Error) > `DENY` > `ESCALATE` > `ALLOW`.
- **Digest Construction**: `inputs_digest` is computed differently (native v1 normalization).

## Migration Guide

To migrate from v0 to v1:
1. run `lumyn migrate your_policy.v0.yml` to generate a draft v1 policy.
2. Review the generated policy (check for any dropped rules or conditions).
3. Test with `lumyn decide` using v1 schema.
