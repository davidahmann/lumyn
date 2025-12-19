# Lumyn v1 Semantics Reference

This document defines the behavior of the Lumyn v1 Decision Engine (`/v1/decide`).

## Evaluation Flow & Stages

`policy.v1` validation logic is strictly ordered into 5 stages. **All rules** in all stages are evaluated; the final verdict is determined by [Verdict Precedence](#verdict-precedence).

### 1. `REQUIREMENTS`
**Goal**: Check for missing data or invalid request structures.
- Typical Verdicts: `DENY` ("Missing Evidence"), `ABSTAIN`.
- Example: "If `evidence.ticket_id` is missing -> DENY".

### 2. `HARD_BLOCKS`
**Goal**: Sanctions, high-risk flags, blocked users.
- Typical Verdicts: `DENY`, `ABSTAIN`.
- Example: "If `evidence.is_sanctioned` is true -> ABSTAIN".

### 3. `ESCALATIONS`
**Goal**: Business rules that require human review (high value, potential risk).
- Typical Verdicts: `ESCALATE`.
- Example: "If `action.amount.value` > $500 -> ESCALATE".

### 4. `ALLOW_PATHS` (formerly Trust Paths)
**Goal**: Safe-lists, known good actors, low-risk fast paths.
- Typical Verdicts: `ALLOW`.
- Example: "If `evidence.customer_tier` is 'VIP' -> ALLOW".

### 5. `DEFAULT`
**Goal**: Fallback if no other rules matched.
- Configured in `defaults.default_verdict`.
- Typically `ESCALATE` (conservative) or `DENY`.

---

## Verdict Precedence

When multiple rules match, the final verdict is chosen by this priority (highest wins):

1. **`ABSTAIN`** (Highest) - The system cannot safely decide (e.g., error, bad data, sanctions).
2. **`DENY`** - Explicitly blocked.
3. **`ESCALATE`** - Needs human review.
4. **`ALLOW`** (Lowest) - Safe to proceed.

*Example*: If one rule says `ALLOW` (Trust Path) but another says `ABSTAIN` (Sanctions), the result is `ABSTAIN`.

---

## Supported Operators

v1 policies only support a strict set of condition keys.

### Action & Amount
- `action_type`: (String) exact match.
- `amount_currency`, `amount_currency_ne`
- `amount_usd`
- `amount_usd_gt`, `amount_usd_gte`, `amount_usd_lt`, `amount_usd_lte`

### Evidence (`evidence.*`)
Evidence keys operate on the `evidence` dictionary in the request. The operator is appended to the key name.
*Format*: `evidence.<evidence_key>_<operator>`

- `_is`: Exact equality.
- `_in`: (List) Value is present in the provided list.
- `_gt`, `_gte`, `_lt`, `_lte`: Numeric comparisons.
- `_ne`: Not equal.

*Example*: `evidence.score_gt: 0.9` checks if `request.evidence.score > 0.9`.

---

## Inputs Digest (v1)

The `inputs_digest` (`determinism.inputs_digest`) is a SHA-256 hash of a canonical JSON payload
containing the request and derived evaluation features (e.g. `amount_usd`).

Treat this value as an opaque, replayable digest that lets you verify “same inputs ⇒ same decision”
across environments.
