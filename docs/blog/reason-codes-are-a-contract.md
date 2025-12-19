---
title: Reason Codes Are A Contract
description: "Stable, machine-readable reason codes unlock production AI governance: reliable dashboards, incident workflows, and audit-ready evidence that natural language explanations cannot provide."
keywords: reason codes, machine-stable codes, AI explainability, audit trail, policy engine, governance, alerting
---

# Reason Codes Are A Contract

**If you want to operate an AI gate in production, your explanations must be more than human-readable prose—they must be machine-stable contracts.** Reason codes are versioned, immutable identifiers that enable monitoring dashboards, incident alerts, and compliance workflows that natural language explanations cannot support.

## The Problem with Dynamic Explanations

Many AI systems return explanations like this:

```json
{
  "verdict": "DENY",
  "explanation": "Chargeback risk detected (confidence: 0.87). User flagged for suspicious activity."
}
```

This seems helpful, but creates operational nightmares:

❌ **Can't alert on it**: Confidence changes every time (0.87 → 0.92 → 0.81)  
❌ **Can't trend it**: Is "suspicious activity" the same as "unusual behavior"?  
❌ **Can't audit it**: What exactly triggered the block—chargeback OR user flag OR both?  
❌ **Can't query it**: No way to count "chargeback blocks" without regex hell

## Why Reason Codes Fix This

Reason codes are **stable machine strings** with no dynamic content:

```json
{
  "verdict": "DENY",
  "reason_codes": [
    "CHARGEBACK_RISK_BLOCK",
    "ACCOUNT_TAKEOVER_RISK_BLOCK"
  ]
}
```

Now you can:

✅ **Alert**: Trigger PagerDuty when `CHARGEBACK_RISK_BLOCK` > 50/hour  
✅ **Trend**: Graph % of denials by reason code over time  
✅ **Audit**: Query: `SELECT COUNT(*) WHERE reason_codes CONTAINS 'CHARGEBACK_RISK_BLOCK'`  
✅ **Replay**: Re-run the decision and get the **same reason codes**

## Reason Codes as Public API

Lumyn treats reason codes as a **versioned, backward-compatible API**:

```python
# src/lumyn/_data/schemas/reason_codes.v1.json
{
  "schema_version": "reason_codes.v1",
  "codes": [
    {
      "code": "CHARGEBACK_RISK_BLOCK",
      "description": "Chargeback risk too high; refund blocked."
    },
    {
      "code": "FAILURE_MEMORY_SIMILAR_BLOCK",
      "description": "Similarity to a labeled failure is high; decision blocked."
    }
  ]
}
```

### The Contract

1. **Stable names**: `CHARGEBACK_RISK_BLOCK` will always mean chargeback risk
2. **No dynamic content**: Never `CHARGEBACK_RISK_BLOCK_87_PERCENT` (that's a metric, not a code)
3. **Versioned schema**: v0 vs v1 reason codes are separate namespaces
4. **Documented semantics**: Each code has a canonical description

This enables **semantic interoperability**: downstream systems (dashboards, tickets, audits) can depend on reason code meaning.

## Lumyn's Production Reason Codes

### Memory-Driven Codes (v1.3+)

When Lumyn's memory system detects similarity to labeled experiences:

| Code | Meaning | Verdict |
|------|---------|---------|
| `FAILURE_MEMORY_SIMILAR_BLOCK` | Similarity to a labeled failure is high | `DENY` |
| `FAILURE_MEMORY_SIMILAR_ESCALATE` | Similarity to a labeled failure is high | `ESCALATE` |
| `SUCCESS_MEMORY_SIMILAR_ALLOW` | Similarity to a labeled success is high | `ALLOW` |

Example:

```json
{
  "verdict": "DENY",
  "reason_codes": ["FAILURE_MEMORY_SIMILAR_BLOCK"],
  "risk_signals": {
    "failure_similarity": {
      "score": 0.94,
      "top_k": [{
        "memory_id": "01JBQW...",
        "label": "failure",
        "score": 0.94,
        "summary": "Fraudulent refund request from compromised account"
      }]
    }
  }
}
```

**Machine-stable code**: `FAILURE_MEMORY_SIMILAR_BLOCK`  
**Dynamic evidence**: `risk_signals.failure_similarity.score = 0.94`  
**Human context**: `summary = "Fraudulent refund..."`

The code is what you alert on. The evidence is what you show in the dashboard. The summary is what operators read during incident response.

### Policy-Driven Codes

From Lumyn's production schema:

| Code | Description |
|------|-------------|
| `REFUND_OVER_ESCALATION_LIMIT` | Refund amount over escalation threshold |
| `SPEND_OVER_APPROVAL_LIMIT` | Spend amount over approval threshold |
| `ACCOUNT_TAKEOVER_RISK_BLOCK` | Account takeover risk too high |
| `PAYMENT_INSTRUMENT_HIGH_RISK` | Payment instrument risk too high |
| `STORAGE_UNAVAILABLE` | Persistence unavailable; decision blocked |
| `MISSING_EVIDENCE_REFUND` | Missing required evidence for refund |

Complete list: [reason_codes.v1.json](https://github.com/davidahmann/lumyn/blob/main/src/lumyn/_data/schemas/reason_codes.v1.json)

## Anti-Patterns: What NOT to Do

### ❌ Dynamic Content in Codes

**Bad**:
```json
{
  "reason_codes": ["CHARGEBACK_RISK_87_PERCENT"]
}
```

**Why**: Next request might be `CHARGEBACK_RISK_92_PERCENT`. Now you have hundreds of unique "reason codes" that are actually metrics.

**Good**:
```json
{
  "reason_codes": ["CHARGEBACK_RISK_BLOCK"],
  "risk_signals": {
    "chargeback_probability": 0.87
  }
}
```

### ❌ Natural Language as Codes

**Bad**:
```json
{
  "reason_codes": ["User might be engaged in suspicious activity based on recent patterns"]
}
```

**Why**: Can't alert on it, can't query it, changes every time.

**Good**:
```json
{
  "reason_codes": ["PATTERN_ANOMALY_DETECTED"],
  "explanation": {
    "summary": "User might be engaged in suspicious activity based on recent patterns"
  }
}
```

### ❌ Mixing Codes and Metrics

**Bad**:
```json
{
  "reason_codes": ["HIGH_RISK", "MEDIUM_CONFIDENCE"]
}
```

**Why**: "HIGH" is relative and changes. Is 0.7 high? Is 0.85 high?

**Good**:
```json
{
  "reason_codes": ["RISK_THRESHOLD_EXCEEDED"],
  "risk_signals": {
    "risk_score": 0.92,
    "confidence": 0.76,
    "threshold": 0.85
  }
}
```

## What This Enables in Production

### 1. Reliable Dashboards

**Query**: Top deny reasons this week

```sql
SELECT 
  reason_code,
  COUNT(*) as count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM decision_records
WHERE verdict = 'DENY'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY reason_code
ORDER BY count DESC;
```

Result:
```
reason_code                       | count | percentage
----------------------------------|-------|----------
CHARGEBACK_RISK_BLOCK             | 1,247 | 42.3%
REFUND_OVER_ESCALATION_LIMIT      | 891   | 30.2%
FAILURE_MEMORY_SIMILAR_BLOCK      | 523   | 17.7%
ACCOUNT_TAKEOVER_RISK_BLOCK       | 289   | 9.8%
```

**Impact**: Product can prioritize fixing the top blocker (chargeback risk model).

### 2. Incident Alerts

**Datadog Monitor**:
```
alert: DENY rate for STORAGE_UNAVAILABLE > 10% of all decisions
query: sum(decisions.deny{reason_code:STORAGE_UNAVAILABLE}) / sum(decisions.total) > 0.1
```

When the database goes down, Lumyn returns:
```json
{
  "verdict": "ABSTAIN",
  "reason_codes": ["STORAGE_UNAVAILABLE"]
}
```

The alert fires immediately because `STORAGE_UNAVAILABLE` is a stable code, not a dynamic error message.

### 3. Audit Workflows

**Compliance requirement**: "Prove how many high-value refunds were blocked due to fraud risk in Q4"

**Query**:
```sql
SELECT COUNT(*)
FROM decision_records
WHERE verdict = 'DENY'
  AND action_type = 'refund'
  AND amount_value > 1000
  AND 'CHARGEBACK_RISK_BLOCK' = ANY(reason_codes)
  AND created_at BETWEEN '2024-10-01' AND '2024-12-31';
```

**Result**: 1,432 high-value refunds blocked for fraud risk

**Proof**: SQL query + Decision Record exports for auditors to replay

### 4. Incident Response: Replay with Same Codes

A customer escalates: "Why was my \$500 refund blocked?"

**Step 1**: Find the Decision Record

```bash
$ lumyn show 01JBQX8P2M...
decision_id: 01JBQX8P2M...
verdict: DENY
reason_codes: CHARGEBACK_RISK_BLOCK, REFUND_OVER_ESCALATION_LIMIT
```

**Step 2**: Export and replay

```bash
$ lumyn export 01JBQX8P2M... --pack --out decision.zip
$ lumyn replay decision.zip
```

**Replay Output**:
```
verdict: DENY
reason_codes: CHARGEBACK_RISK_BLOCK, REFUND_OVER_ESCALATION_LIMIT
matched_rules: R_FRAUD_BLOCK (HARD_BLOCKS)
```

**Result**: Decision is deterministic. Same codes, same verdict, reproducible evidence for customer support.

## Implementing Reason Codes in Your System

### Define Your Code Schema

```json
{
  "schema_version": "reason_codes.v1",
  "codes": [
    {
      "code": "APPROVAL_LIMIT_EXCEEDED",
      "description": "Request amount over approval threshold",
      "severity": "medium"
    },
    {
      "code": "FRAUD_MODEL_HIGH_RISK",
      "description": "Fraud detection model flagged high risk",
      "severity": "high"
    }
  ]
}
```

### Return Codes in Decisions

```python
from lumyn import decide

record = decide(
    request={
        "action": {"type": "refund", "amount": {"value": 500, "currency": "USD"}},
        # ...
    },
    config=LumynConfig(policy_path="policy.yml")
)

# Reason codes are guaranteed to be stable strings
assert isinstance(record["reason_codes"], list)
assert all(isinstance(code, str) for code in record["reason_codes"])

# Use codes for alerting/dashboards
for code in record["reason_codes"]:
    metrics.increment(f"decisions.reason_code.{code}")
```

### Policy Rules Emit Codes

```yaml
# policy.yml
rules:
  - id: R_REFUND_LIMIT
    stage: ESCALATIONS
    if:
      action_type: "refund"
      amount_usd: { gt: 250 }
    then:
      verdict: ESCALATE
      reason_codes:
        - REFUND_OVER_ESCALATION_LIMIT
```

When this rule matches, the Decision Record includes `REFUND_OVER_ESCALATION_LIMIT` as a stable, machine-readable code.

## Reason Codes + Human Explanations

Reason codes don't replace human-readable explanations—they complement them:

```json
{
  "verdict": "DENY",
  "reason_codes": ["FAILURE_MEMORY_SIMILAR_BLOCK"],
  "explanation": {
    "summary": "This request is very similar to a previously labeled failed transaction that resulted in a chargeback.",
    "details": "Similarity score: 0.94. Matched memory: 01JBQW..."
  }
}
```

- **Reason codes**: For machines (alerts, dashboards, queries)
- **Explanation**: For humans (customer support, incident investigation)

Both are essential. Reason codes enable **operational workflows**, explanations enable **human understanding**.

## Frequently Asked Questions

### Can reason codes change between versions?

Yes, but with semantic versioning. v0 reason codes are separate from v1 codes. Use `schema_version: "reason_codes.v1"` to lock your dependency. Lumyn guarantees v1 codes won't change meaning within the v1 namespace.

### How do I handle deprecated reason codes?

Add new codes, but keep old ones for backward compatibility. Mark deprecated codes in documentation:

```json
{
  "code": "OLD_FRAUD_BLOCK",
  "description": "Deprecated. Use CHARGEBACK_RISK_BLOCK instead.",
  "deprecated": true,
  "deprecated_since": "v1.2.0",
  "replacement": "CHARGEBACK_RISK_BLOCK"
}
```

### Should I create a unique code for every rule?

No. Use **semantic grouping**. Multiple rules can emit the same reason code if they represent the same underlying policy concern.

Example:
- Rule R_HIGH_AMOUNT → `REFUND_OVER_ESCALATION_LIMIT`
- Rule R_REPEATED_REFUNDS → `REFUND_PATTERN_ANOMALY`

Both are about refunds, but different policy concerns = different codes.

### How granular should reason codes be?

**Rule of thumb**: If you would create a separate Datadog alert or dashboard chart for it, it deserves its own code.

Too granular: `REFUND_500_USD`, `REFUND_501_USD` (use metrics instead)  
Too broad: `POLICY_VIOLATION` (which policy?)  
Just right: `REFUND_OVER_ESCALATION_LIMIT`

### Can one decision have multiple reason codes?

Yes! Lumyn returns all applicable codes:

```json
{
  "verdict": "DENY",
  "reason_codes": [
    "CHARGEBACK_RISK_BLOCK",
    "ACCOUNT_TAKEOVER_RISK_BLOCK"
  ]
}
```

This means: "Blocked due to BOTH chargeback risk AND account takeover signals."

## Next Steps

- **[v1 Semantics](/docs/v1_semantics)** - Understand how reason codes map to verdicts in Lumyn's evaluation engine
- **[Replay Guarantees](/docs/replay-guarantees)** - See how reason codes enable deterministic replay
- **[What is a Decision Record?](/blog/what-is-a-decision-record)** - Learn about the full Decision Record structure
- **[Lumyn Memory](/docs/memory)** - Explore memory-driven reason codes like `FAILURE_MEMORY_SIMILAR_BLOCK`
