---
title: "AI Incident Response: Replay Decisions"
description: "Treat every AI incident like a reproducible bug. Replay the decision, label outcomes as append-only events, and re-run deterministically to prove the fix worked."
keywords: AI incident response, decision replay, deterministic AI, policy debugging, memory labeling, feedback loop
---

# AI Incident Response: Replay Decisions

**When an AI-powered workflow causes an incident, teams often fall back to guesswork: screenshots, partial logs, and "maybe the prompt changed."** Lumyn's incident workflow is simpler: Record every gated action as a Decision Record, replay deterministically to reproduce verdict + reasons, label outcomes as append-only events, and re-run the same request to confirm behavior changes.

## The Traditional AI Incident Problem

A customer escalates: "Your AI unfairly blocked my \$500 refund!"

**Traditional debugging**:
1. Check application logs → find "refund denied" message
2. Check APM traces → see 200 OK response
3. Ask engineering: "What was the prompt?" → Nobody knows
4. Ask product: "Did the model change?" → Maybe?
5. Conclusion: "Sorry, we can't reproduce this"

**Problem**: No replayable evidence. The decision is gone.

## The Replay-Based Incident Workflow

Lumyn treats every incident like a **reproducible bug** with verifiable evidence:

```
┌─────────────────────────────────────────────────┐
│ 1. RECORD                                       │
│    Every decision → Decision Record             │
│    (verdict + reasons + policy hash + digest)   │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ 2. REPLAY                                       │
│    lumyn replay decision.zip                    │
│    → Same verdict + Same reasons                │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ 3. LABEL                                        │
│    lumyn label <decision_id> --label failure    │
│    → Memory learns from incident                │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ 4. RE-RUN                                       │
│    Submit same request again                    │
│    → Verify behavior changed                    │
└─────────────────────────────────────────────────┘
```

## Step 1: Record Every Decision

### Automatic Recording

Every time Lumyn makes a decision, it returns a **Decision Record**:

```python
from lumyn import decide, LumynConfig

# Make a decision
record = decide(
    request={
        "subject": {"type": "user", "id": "usr_abc123"},
        "action": {
            "type": "refund",
            "amount": {"value": 500, "currency": "USD"}
        },
        "context": {"mode": "inline", "inline": {...}, "digest": "sha256:..."}
    },
    config=LumynConfig(policy_path="policy.yml")
)

print(record["decision_id"])  # "01JBQX8P2M..."
print(record["verdict"])       # "DENY"
print(record["reason_codes"])  # ["CHARGEBACK_RISK_BLOCK"]
```

This Decision Record is stored in `.lumyn/lumyn.db` with full context:
- Original request (inputs_digest)
- Policy version (policy_hash)
- Matched rules
- Risk signals (memory similarity, uncertainty)
- Timestamp

### Export for Replay

```bash
# Export decision as a portable ZIP pack
$ lumyn export 01JBQX8P2M... --pack --out decision_incident_123.zip

# decision_incident_123.zip contains:
# - decision_record.json (full Decision Record)
# - request.json (original DecisionRequest)
# - policy.yml (policy snapshot at decision time)
# - README.txt (replay instructions)
```

Now you have **reproducible evidence** that can be shared with support, engineering, or auditors.

## Step 2: Replay Deterministically

### Reproduce the Exact Decision

```bash
$ lumyn replay decision_incident_123.zip
```

**Output**:
```
Replaying decision 01JBQX8P2M...

verdict: DENY
reason_codes: CHARGEBACK_RISK_BLOCK, REFUND_OVER_ESCALATION_LIMIT

matched_rules:
  - HARD_BLOCKS:R_FRAUD_BLOCK effect=DENY reasons=['CHARGEBACK_RISK_BLOCK']
  - ESCALATIONS:R_REFUND_LIMIT effect=ESCALATE reasons=['REFUND_OVER_ESCALATION_LIMIT']

risk_signals:
  failure_similarity: 0.87
  uncertainty_score: 0.23

Replay successful: verdict matches original.
```

**Replay guarantees**:
- ✅ Same verdict (`DENY`)
- ✅ Same reason codes  
- ✅ Same matched rules
- ✅ Same risk signals (if memory state is identical)

### What Gets Reproduced

| Element | Reproduced? | Notes |
|---------|------------|-------|
| **Verdict** | ✅ Yes | Exact same: ALLOW, DENY, ABSTAIN, or ESCALATE |
| **Reason codes** | ✅ Yes | Stable machine strings |
| **Matched rules** | ✅ Yes | Same policy evaluation sequence |
| **Timestamps** | ❌ No | `created_at` and `decision_id` are new |
| **Memory similarity** | ⚠️ Maybe | Only if memory state hasn't changed |
| **External API calls** | ❌ No | Must mock or record separately |

### Why Replay Matters

**Without replay**:
> "The AI blocked the refund, but we don't know why. Engineering can't reproduce it. Customer is angry."

**With replay**:
> "Here's the exact decision. We can replay it and see verdict + reasons. Root cause: chargeback risk model triggered. Customer support can explain precisely what happened."

## Step 3: Label Outcomes for Learning

### The Feedback Loop

After investigating the incident, you determine the decision was **wrong**:

```bash
# Label the decision as a failure
$ lumyn label 01JBQX8P2M... --label failure --summary "False positive: legitimate customer"
```

**What this does**:
1. Creates an append-only event: `{type: "label", data: {label: "failure"}}`
2. Adds decision to **memory store** with `outcome=-1` (failure)
3. Future similar requests will trigger `FAILURE_MEMORY_SIMILAR_BLOCK` reason code

### Memory-Driven Learning

Next time a similar request comes in:

```json
{
  "verdict": "ESCALATE",
  "reason_codes": ["FAILURE_MEMORY_SIMILAR_ESCALATE"],
  "risk_signals": {
    "failure_similarity": {
      "score": 0.91,
      "top_k": [{
        "memory_id": "01JBQW...",
        "label": "failure",
        "score": 0.91,
        "summary": "False positive: legitimate customer"
      }]
    }
  }
}
```

**Result**: AI now escalates instead of auto-denying because it learned from the incident.

### Append-Only Events

Labels are **append-only** (never mutate past decisions):

```bash
# View decision history
$ lumyn show 01JBQX8P2M...

decision_id: 01JBQX8P2M...
verdict: DENY
reason_codes: CHARGEBACK_RISK_BLOCK

events:
  - 2024-12-19T14:30:00Z | type: label | data: {label: "failure"}
  - 2024-12-19T14:35:00Z | type: note  | data: {text: "Customer escalation #5432"}
```

This preserves **audit trail integrity**: You can see the original decision AND the post-incident labeling.

## Step 4: Re-Run to Verify Fix

### Confirm Behavior Changed

After labeling the failure, submit the same request again:

```python
# Original request (from replayed decision pack)
request = {
    "subject": {"type": "user", "id": "usr_abc123"},
    "action": {"type": "refund", "amount": {"value": 500, "currency": "USD"}},
    "context": {"mode": "inline", "inline": {...}, "digest": "sha256:..."}
}

# Re-run decision with updated memory
new_record = decide(request, config=LumynConfig(policy_path="policy.yml"))

print(new_record["verdict"])       # "ESCALATE" (was "DENY")
print(new_record["reason_codes"])  # ["FAILURE_MEMORY_SIMILAR_ESCALATE"]
```

**Verification**:
- ✅ Verdict changed: `DENY` → `ESCALATE`
- ✅ Memory learning worked
- ✅ False positive reduced (no longer auto-denies)

### Incident Resolution Workflow

```
┌─────────────────────────────────────────────────┐
│ Incident: Customer escalation #5432             │
│ "AI unfairly blocked my \$500 refund"           │
└─────────────────────────────────────────────────┘
              ↓
    ┌──────────────────┐
    │ INVESTIGATE      │
    │ lumyn replay     │
    │ → DENY verdict   │
    │ → False positive │
    └──────────────────┘
              ↓
    ┌──────────────────┐
    │ LABEL            │
    │ lumyn label      │
    │ --label failure  │
    └──────────────────┘
              ↓
    ┌──────────────────┐
    │ VERIFY           │
    │ Re-run request   │
    │ → ESCALATE now   │
    └──────────────────┘
              ↓
    ┌──────────────────┐
    │ CLOSE TICKET     │
    │ AI learned       │
    │ Won't auto-deny  │
    └──────────────────┘
```

## Real-World Incident Scenarios

### Scenario 1: Policy Too Strict

**Incident**: 50 legitimate refunds blocked in 1 hour

**Investigation**:
```bash
$ lumyn export --query "verdict=DENY AND action_type=refund AND created_at > '2024-12-19 14:00'"
# → Exports 50 decision packs

$ for pack in decision_*.zip; do
    lumyn replay $pack | grep "reason_codes"
  done

# Result: All 50 have "REFUND_OVER_ESCALATION_LIMIT"
```

**Root Cause**: Escalation threshold too low (\$250)

**Fix**: Update policy to \$500 threshold

**Verification**:
```yaml
# policy.yml
rules:
  - id: R_REFUND_LIMIT
    if:
      amount_usd: { gt: 500 }  # Was 250
    then:
      verdict: ESCALATE
      reason_codes: ["REFUND_OVER_ESCALATION_LIMIT"]
```

**Regression test**:
```bash
$ for pack in decision_*.zip; do
    lumyn replay $pack --policy new_policy.yml
  done

# Result: 48/50 now ALLOW, 2/50 still ESCALATE (correctly)
```

### Scenario 2: Memory False Positive

**Incident**: High-value customer blocked due to memory

**Investigation**:
```bash
$ lumyn show 01JBQX8P2M...

verdict: DENY
reason_codes: FAILURE_MEMORY_SIMILAR_BLOCK
risk_signals:
  failure_similarity: 0.94
  top_k: [memory_id: 01JBQW...]
```

**Root Cause**: Memory item 01JBQW was mislabeled as "failure"

**Fix**:
```bash
# Re-label the source memory as "success"
$ lumyn label 01JBQW... --label success --summary "Actually legitimate transaction"
```

**Verification**:
```bash
$ lumyn replay decision_01JBQX.zip
# Now similarity to "success" is high, not "failure"
# Verdict changes to ALLOW
```

### Scenario 3: Storage Outage Abstentions

**Incident**: 1,000 ABSTAIN verdicts during database downtime

**Investigation**:
```bash
$ lumyn export --query "verdict=ABSTAIN AND created_at BETWEEN '14:25' AND '14:32'"

$ lumyn replay decision_01JBQX.zip
# verdict: ABSTAIN
# reason_codes: STORAGE_UNAVAILABLE
```

**Root Cause**: Database connection pool exhausted

**Verification**:
```bash
# After DB fix, replay decisions
$ lumyn replay decision_01JBQX.zip
# verdict: ALLOW (was ABSTAIN)
# reason_codes: REFUND_SMALL_LOW_RISK
```

**Result**: Confirmed decisions would have succeeded with healthy storage.

## CLI Reference

### Export Decision Packs

```bash
# Export single decision
lumyn export <decision_id> --pack --out decision.zip

# Export by query
lumyn export --query "verdict=DENY AND action_type=refund"

# Export last 100 decisions
lumyn export --limit 100 --out decisions.jsonl
```

### Replay Decisions

```bash
# Replay with current policy
lumyn replay decision.zip

# Replay with candidate policy (regression testing)
lumyn replay decision.zip --policy candidate_policy.yml

# Replay and show markdown summary
lumyn replay decision.zip --markdown
```

### Label Outcomes

```bash
# Label as failure
lumyn label <decision_id> --label failure --summary "False positive"

# Label as success
lumyn label <decision_id> --label success --summary "Correctly allowed"

# Add note (doesn't affect memory)
lumyn label <decision_id> --label note --summary "Customer escalation #5432"
```

### Diff Policy Changes

```bash
# Test candidate policy against past decisions
lumyn diff dataset.jsonl --policy candidate_policy.yml

# Output: Shows which decisions would change
Changes: 23
decision_id       | old    | new     | reason_diff
01JBQX8P2M...     | DENY   | ALLOW   | [CHARGEBACK_RISK] → [LOW_RISK]
```

## Frequently Asked Questions

### Can I replay decisions from weeks ago?

Yes, if you exported the decision pack and pinned your Lumyn version. The `inputs_digest` and `policy_hash` ensure deterministic replay. If you upgrade Lumyn, older decision packs may produce different results (expected behavior).

### What if my memory store has changed since the original decision?

Replay uses the **current memory state**, not the original. If you labeled new failures since the decision, similarity scores will differ. For audit reproducibility, snapshot your memory database along with the decision pack.

### How do I replay a decision that called an external API?

External calls (fraud APIs, ML models) are **not** replayed. You must mock them or store their responses in the decision pack. Lumyn's replay guarantee only covers the **policy engine evaluation**, not external dependencies.

### Can I replay decisions in a different environment (dev/staging)?

Yes, but be aware:
- Memory state might differ
- External API responses might differ
- Policy might have diverged

Use `lumyn diff` to test policy changes before deploying to production.

### How do I prevent memory poisoning (bad labels)?

Memory is **append-only**. If you mislabel a decision, you can:
1. Add a corrective label: `lumyn label <decision_id> --label success` (overrides previous failure label)
2. Prune memory: Remove the memory_id from `.lumyn/memory` database (requires direct SQL)

Best practice: Review labels before adding them, especially for high-impact decisions.

## Next Steps

- **[Replay Guarantees](/docs/replay-guarantees)** - Understand deterministic replay contracts and limitations
- **[Lumyn Memory](/docs/memory)** - Deep dive into memory labeling and learning feedback loops
- **[What is a Decision Record?](/blog/what-is-a-decision-record)** - Learn about Decision Record structure and schema
- **[Reason Codes Are A Contract](/blog/reason-codes-are-a-contract)** - Understand stable reason codes for incident alerts
