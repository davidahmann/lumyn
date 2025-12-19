---
title: Decision Logs vs Telemetry
description: "Telemetry monitors system health; Decision Records explain policy outcomes. Learn when to use each and how they work together for production AI governance."
keywords: decision logs, telemetry, APM, observability, policy engine, distributed tracing, audit logs
---

# Decision Logs vs Telemetry

**Telemetry tells you what the system did (latency, errors, traces). Decision Records tell you why an action was allowed or denied.** They serve different purposes: telemetry monitors system health and performance, while Decision Records provide governance and audit evidence for policy-driven decisions. Production AI systems need both, but for fundamentally different workflows.

## The Critical Gap Telemetry Can't Fill

When an AI-powered refund gets blocked, a content publish fails moderation, or a high-value transaction triggers escalation, your telemetry shows:

```
POST /api/v1/decide returned 200 OK in 230ms
spans: gateway → policy-engine → memory-store
```

But it doesn't answer the operator's critical question:

> **"Why was this specific action blocked?"**

This is where Decision Records become essential.

## What Telemetry Captures

### System Behavior & Performance

Modern APM and distributed tracing excels at:

| Telemetry Data | Purpose | Tools |
|--------|---------|-------|
| **Request latency** | P50/P95/P99 performance monitoring | Datadog, New Relic, Honeycomb |
| **Error rates** | System reliability tracking | Sentry, Rollbar |
| **Distributed traces** | Request flow across services | Jaeger, Zipkin, OpenTelemetry |
| **Resource metrics** | CPU, memory, disk usage | Prometheus, Grafana |

Example trace from Lumyn:

```json
{
  "trace_id": "4bf92f3577b34da6",
  "spans": [
    {"name": "POST /v1/decide", "duration_ms": 234},
    {"name": "lumyn.decide_v1", "duration_ms": 226},
    {"name": "policy.evaluate", "duration_ms": 12},
    {"name": "memory.search", "duration_ms": 198}
  ]
}
```

**What this tells you**: The request took 234ms total, with most time spent in memory search.

**What this doesn't tell you**: Whether the decision was ALLOW or DENY, which policy rules matched, or why memory influenced the verdict.

## What Decision Records Capture

### Policy Outcomes & Governance Evidence

Decision Records capture the **policy evaluation context**:

| Decision Record Data | Purpose |
|---------------------|---------|
| **Verdict** | `ALLOW \| DENY \| ABSTAIN \| ESCALATE` |
| **Reason codes** | Machine-stable explanation (`FAILURE_MEMORY_SIMILAR_BLOCK`) |
| **Matched rules** | Which policy rules fired during evaluation |
| **Risk signals** | Memory similarity scores, uncertainty metrics |
| **Determinism proof** | Policy hash, inputs digest for replay |

Example Decision Record from Lumyn:

```json
{
  "decision_id": "01JBQX8P2M...",
  "verdict": "DENY",
  "reason_codes": [
    "FAILURE_MEMORY_SIMILAR_BLOCK",
    "CHARGEBACK_RISK_BLOCK"
  ],
  "matched_rules": [
    {
      "rule_id": "R_FRAUD_BLOCK",
      "stage": "HARD_BLOCKS",
      "effect": "DENY"
    }
  ],
  "risk_signals": {
    "failure_similarity": {
      "score": 0.94,
      "top_k": [{
        "memory_id": "01JBQW...",
        "label": "failure",
        "score": 0.94
      }]
    }
  }
}
```

**What this tells you**: The decision was DENY because it matched a HARD_BLOCKS rule and had 94% similarity to a previously labeled failure.

**What this doesn't tell you**: How long the request took or which services were involved (that's telemetry's job).

## Side-by-Side Comparison

### Incident Scenario: Refund Request Blocked

A customer complains their \$500 refund was blocked. Here's what each system shows:

**Telemetry View** (APM/Traces):
```
✓ POST /api/refund → 200 OK in 310ms
  ├─ auth-service: 45ms
  ├─ policy-engine: 230ms  
  └─ database: 35ms

✓ No errors, all spans green
✓ Latency within SLO (P95 < 500ms)
```

**Verdict**: System is healthy, no errors.

**Decision Record View**:
```json
{
  "decision_id": "01JBQX8P2M...",
  "verdict": "DENY",
  "reason_codes": [
    "CHARGEBACK_RISK_BLOCK",
    "REFUND_OVER_ESCALATION_LIMIT"
  ],
  "matched_rules": [
    {"rule_id": "R_REFUND_LIMIT", "stage": "ESCALATIONS"}
  ]
}
```

**Verdict**: Blocked because amount exceeded \$250 limit AND chargeback risk detected.

**The Gap**: Telemetry shows the system worked fine. Decision Record shows **why the policy denied it**.

## When Telemetry Fails for Decision Forensics

### 1. Non-Exception Failures

In gated AI actions, the "failure" is often a **policy decision**, not a system error:

```python
# This returns 200 OK with DENY verdict
record = decide(request)
assert record["verdict"] == "DENY"  # Not an exception!
```

Telemetry sees: ✅ 200 OK, no errors
Reality: ❌ Decision was blocked by policy

### 2. Missing Context

Telemetry logs show function calls but miss **why that code path was taken**:

```
[INFO] Evaluating policy stage: HARD_BLOCKS
[INFO] Rule R_FRAUD matched
[INFO] Verdict: DENY
```

vs Decision Record:

```json
{
  "matched_rules": [{
    "rule_id": "R_FRAUD",
    "stage": "HARD_BLOCKS",
    "effect": "DENY",
    "reason_codes": ["CHARGEBACK_RISK_BLOCK"]
  }],
  "risk_signals": {
    "failure_similarity": {"score": 0.87}
  }
}
```

The trace shows *that* R_FRAUD matched. The Decision Record shows *why* (87% similarity to past failures).

### 3. Reproducibility

Telemetry traces are **ephemeral** and **non-deterministic**:
- Trace sampling might miss the problematic request
- Timing/latency varies on every request
- No guarantee you can reproduce the exact outcome

Decision Records are **durable** and **deterministic**:
- Every decision gets a Decision Record (not sampled)
- `inputs_digest` + `policy_hash` = reproducible replay
- Run `lumyn replay decision_pack.zip` to re-execute the exact decision

## How They Work Together

### The Ideal Setup: Both Systems in Production

```python
from lumyn import decide
import opentelemetry.tracing as otel

# 1. Telemetry: Distributed tracing
with otel.start_span("refund_request") as span:
    span.set_attribute("user_id", "usr_123")
    span.set_attribute("amount", 500)
    
    # 2. Decision Record: Policy governance
    record = decide(request, config=LumynConfig(policy_path="policy.yml"))
    
    # 3. Enrich telemetry with decision context
    span.set_attribute("decision.verdict", record["verdict"])
    span.set_attribute("decision.id", record["decision_id"])
    span.set_attribute("decision.reason_codes", record["reason_codes"])

# Now you have:
# - Telemetry: Request flow, latency, errors
# - Decision Record: Policy verdict, reason codes, reproducibility
```

### Integration Patterns

| Scenario | Use Telemetry | Use Decision Record |
|----------|--------------|-------------------|
| **System is slow** | ✅ Trace latency spikes | ❌ Not performance-relevant |
| **Why was X blocked?** | ❌ Doesn't capture policy logic | ✅ Shows matched rules + reasons |
| **P95 latency regression** | ✅ Compare traces over time | ❌ Not latency-related |
| **Audit compliance** | ❌ Traces are sampled/ephemeral | ✅ Full decision audit trail |
| **Memory corruption detected** | ✅ Error logs + traces | ❌ Not a decision issue |
| **False positive rate rising** | ❌ No verdict context | ✅ Track DENY → labeled SUCCESS |
| **Service dependency issue** | ✅ Distributed trace map | ❌ Not service health |
| **Incident replay** | ❌ Can't reproduce exact behavior | ✅ Deterministic replay via `lumyn replay` |

### Dashboard Example: Combining Both

```
┌─ System Health (Telemetry) ────────────────┐
│ Requests/sec: 1,234                        │
│ P95 latency: 245ms                         │
│ Error rate: 0.03%                          │
└────────────────────────────────────────────┘

┌─ Decision Outcomes (Decision Records) ─────┐
│ ALLOW: 82%  ▓▓▓▓▓▓▓▓░░                    │
│ DENY: 12%   ▓▓░░░░░░░░                    │
│ ESCALATE: 6% ▓░░░░░░░░░                   │
│                                            │
│ Top Deny Reasons:                          │
│ 1. CHARGEBACK_RISK_BLOCK (45%)             │
│ 2. REFUND_OVER_ESCALATION_LIMIT (32%)     │
│ 3. FAILURE_MEMORY_SIMILAR_BLOCK (18%)     │
└────────────────────────────────────────────┘
```

## Real-World Integration: Incident Response Workflow

### Step 1: Telemetry Detects Anomaly

```
Alert: /api/refund error rate spike
Error rate: 0.03% → 2.4% (80x increase)
Time: 2024-12-19 14:30:00 UTC
```

### Step 2: Query Decision Records for Context

```sql
SELECT verdict, reason_codes, COUNT(*) as count
FROM decision_records
WHERE created_at > '2024-12-19 14:25:00'
  AND action_type = 'refund'
GROUP BY verdict, reason_codes
ORDER BY count DESC;
```

Result:
```
DENY | ["STORAGE_UNAVAILABLE"] | 1,247
```

### Step 3: Root Cause Found

**Telemetry** shows: Error rate spike at 14:30  
**Decision Records** show: All denies have `STORAGE_UNAVAILABLE` reason code  
**Root Cause**: Database connection pool exhausted → policy engine abstained

### Step 4: Replay for Verification

```bash
# Replay one of the failed decisions after DB fix
lumyn replay decision_01JBQX.zip

# Output:
# verdict: ALLOW (was DENY during incident)
# reason_codes: ["REFUND_SMALL_LOW_RISK"]
```

Result: Confirmed that decisions would have succeeded with healthy database.

## Frequently Asked Questions

### Should I replace my APM with Decision Records?

No. They serve complementary purposes. Keep your APM (Datadog, New Relic, etc.) for system health monitoring. Add Decision Records for **policy governance and audit evidence**.

### Can Decision Records show request latency?

No, that's telemetry's job. Decision Records focus on **decision context** (verdict, reasons, policy state), not performance metrics. Enrich your telemetry spans with `decision_id` to correlate both systems.

### Do Decision Records work with OpenTelemetry?

Yes. Lumyn emits OpenTelemetry spans for `lumyn.decide_v1`, `policy.evaluate`, and `memory.search`. You can correlate Decision Records with traces using the `decision_id` attribute.

### How do I store both telemetry and Decision Records cost-effectively?

- **Telemetry**: Sample traces (1-10%), retain for 7-30 days
- **Decision Records**: Store 100% of decisions, retain verdict+reasons forever (2-10 KB each), full records for 90 days

The decision verdict is your **audit trail**, so keep it. Detailed traces are for debugging, so sampling is fine.

### What if my telemetry already captures logs with "decision: DENY"?

That's a good start, but logs are unstructured and non-reproducible. Decision Records provide:
1. **Schema validation** (can't log malformed verdicts)
2. **Cryptographic digests** (replay with `lumyn replay`)
3. **Normalized reason codes** (alert on specific codes, not regex)
4. **Memory integration** (similarity scores, learning feedback)

Structured Decision Records > grepping logs for "DENY".

## Next Steps

- **[What is a Decision Record?](/blog/what-is-a-decision-record)** - Deep dive into Decision Record structure
- **[Replay Guarantees](/docs/replay-guarantees)** - Learn about deterministic replay for incident response
- **[Integration Checklist](/docs/integration_checklist)** - Add Decision Records to your existing observability stack
- **[Lumyn Memory](/docs/memory)** - Understand how memory similarity appears in Decision Records
