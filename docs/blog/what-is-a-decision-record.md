---
title: What is a Decision Record?
description: "A Decision Record is a durable, replayable receipt for gated AI actions containing verdict, stable reason codes, and cryptographic digests for reproducibility."
keywords: decision record, AI governance, decision logging, policy engine, audit trail, reproducible AI, reason codes
---

# What is a Decision Record?

**A Decision Record is a durable, replayable receipt for every gated action in production AI systems.** Unlike traditional logs, it captures the complete decision context—verdict, stable machine-readable reason codes, policy snapshot, and cryptographic digests—enabling deterministic replay for incident response, audits, and compliance workflows.

## Why Decision Records Matter for Production AI

When your AI system denies a refund, blocks a content publish, or escalates a high-risk transaction, you need more than "the request failed." You need:

- **What verdict was issued** (`ALLOW`, `DENY`, `ABSTAIN`, or `ESCALATE`)
- **Why that verdict was chosen** (stable reason codes like `FAILURE_MEMORY_SIMILAR_BLOCK`)
- **Reproducible evidence** (policy hash, inputs digest, evaluation order)

Decision Records provide this structured evidence layer that traditional telemetry and application logs cannot.

## What's Inside a Decision Record?

### The Four Verdict Types

Every Decision Record contains one of four normalized verdicts:

| Verdict | Meaning | Use Case |
|---------|---------|----------|
| `ALLOW` | Action permitted by policy | Low-risk refunds, trusted users |
| `DENY` | Action blocked by policy | High chargeback risk, policy violations |
| `ABSTAIN` | Insufficient information to decide | Missing required evidence, storage unavailable |
| `ESCALATE` | Requires human review | Amount over approval limit, anomaly detected |

### Stable Reason Codes

Reason codes are **machine-stable strings** (no dynamic content) that explain the verdict:

```json
{
  "verdict": "DENY",
  "reason_codes": [
    "FAILURE_MEMORY_SIMILAR_BLOCK",
    "REFUND_OVER_ESCALATION_LIMIT"
  ]
}
```

Example reason codes from Lumyn's implementation:
- `FAILURE_MEMORY_SIMILAR_BLOCK` - Similarity to a labeled failure is high; decision blocked
- `SUCCESS_MEMORY_SIMILAR_ALLOW` - Similarity to a labeled success is high; decision allowed  
- `MISSING_EVIDENCE_REFUND` - Missing required evidence for refund
- `CHARGEBACK_RISK_BLOCK` - Chargeback risk too high; refund blocked
- `ACCOUNT_TAKEOVER_RISK_BLOCK` - Account takeover risk too high; action blocked

**Why stable codes matter**: You can alert on `CHARGEBACK_RISK_BLOCK` rising 40% week-over-week. You can't alert on "chargeback risk detected (confidence: 0.87)" because the confidence changes every time.

### Determinism & Replay Guarantees

Decision Records include cryptographic digests that make decisions reproducible:

```json
{
  "determinism": {
    "engine_version": "1.3.0",
    "evaluation_order": ["REQUIREMENTS", "HARD_BLOCKS", "ESCALATIONS", "ALLOW_PATHS", "DEFAULT"],
    "inputs_digest": "sha256:a4f2c8..."
  },
  "policy": {
    "policy_id": "fraud-prevention",
    "policy_version": "2.1.0",
    "policy_hash": "sha256:b3e5d9..."
  }
}
```

**Replay guarantee**: If you replay the same Decision Record with the same Lumyn version, you get the same verdict and reason codes. This enables:
- **Incident response**: Reproduce the exact decision that caused the issue
- **Regression testing**: Verify policy changes don't break existing decisions
- **Audit compliance**: Prove decisions are deterministic and traceable

## How Decision Records Compare to Alternatives

### vs. Application Logs

| Feature | App Logs | Decision Records |
|---------|----------|-----------------|
| **Structure** | Unstructured text | Normalized JSON schema |
| **Reproducibility** | Non-deterministic | Cryptographically verified |
| **Alerting** | Regex on log messages | Machine-stable reason codes |
| **Audit trail** | Partial, often incomplete | Complete decision context |

### vs. Telemetry (APM/Traces)

Telemetry tells you **what the system did** (latency, errors, traces). Decision Records tell you **why an action was allowed or denied**.

Example:
- **Telemetry**: "POST /api/refund returned 403 in 230ms"
- **Decision Record**: "Returned `DENY` because `FAILURE_MEMORY_SIMILAR_BLOCK` (similarity: 0.94 to decision_id: 01JBQX...)"

You need both. Telemetry for system health, Decision Records for decision forensics.

### vs. Audit Logs

Traditional audit logs capture "who did what, when" but miss **why the policy engine made that choice**. Decision Records capture:
- Which policy rules matched
- Which memory items influenced the decision  
- What risk signals were detected
- The complete evaluation sequence

## Real-World Use Cases

### 1. Fraud Prevention

A fintech customer uses Decision Records to prove compliance during audits:

```json
{
  "decision_id": "01JBQX8P2M...",
  "verdict": "DENY",
  "reason_codes": ["CHARGEBACK_RISK_BLOCK", "PAYMENT_INSTRUMENT_HIGH_RISK"],
  "matched_rules": [
    {
      "rule_id": "R_FRAUD_001",
      "stage": "HARD_BLOCKS",
      "effect": "DENY"
    }
  ]
}
```

When regulators ask "Why was transaction X blocked?", they replay the Decision Record and show the exact policy rule + risk signals.

### 2. AI Safety Gates

A content moderation platform uses Decision Records to track "allow" decisions that later became incidents:

1. Decision allows content publish (`ALLOW` + `LOW_RISK_CLASSIFICATION`)
2. Content goes viral with harmful misinformation
3. Team labels the decision as `FAILURE` using `lumyn label`
4. Memory system learns: future similar content gets `ABSTAIN` or `ESCALATE`
5. Decision Record shows the learning feedback loop in action

### 3. Customer Support Escalations

A SaaS company uses the `ESCALATE` verdict for high-value requests:

```json
{
  "verdict": "ESCALATE",
  "reason_codes": ["REFUND_OVER_ESCALATION_LIMIT"],
  "obligations": [
    {
      "type": "required_evidence",
      "title": "Manager Approval Required",
      "fields": ["manager_email", "justification"]
    }
  ]
}
```

The Decision Record creates a ticket with structured obligations, not just "needs review."

## Decision Record Schema (v1)

Here's what a complete Decision Record looks like in Lumyn:

```json
{
  "schema_version": "decision_record.v1",
  "decision_id": "01JBQX8P2M...",
  "created_at": "2024-12-19T14:30:00Z",
  "verdict": "ALLOW",
  "reason_codes": ["SUCCESS_MEMORY_SIMILAR_ALLOW", "REFUND_SMALL_LOW_RISK"],
  "matched_rules": [...],
  "risk_signals": {
    "uncertainty_score": 0.12,
    "failure_similarity": {
      "score": 0.23,
      "top_k": [...]
    },
    "success_similarity": {
      "score": 0.91,
      "top_k": [...]
    }
  },
  "queries": [],
  "obligations": [],
  "determinism": {
    "engine_version": "1.3.0",
    "evaluation_order": [...],
    "inputs_digest": "sha256:..."
  }
}
```

## Getting Started with Decision Records

Implementing Decision Records in your system:

```python
from lumyn import decide, LumynConfig

# Make a decision
record = decide(
    request={
        "subject": {"type": "user", "id": "usr_123"},
        "action": {"type": "refund", "amount": {"value": 50, "currency": "USD"}},
        "context": {"mode": "inline", "inline": {...}, "digest": "sha256:..."}
    },
    config=LumynConfig(policy_path="policy.yml")
)

# Access structured verdict
print(record["verdict"])  # "ALLOW" | "DENY" | "ABSTAIN" | "ESCALATE"
print(record["reason_codes"])  # ["REFUND_SMALL_LOW_RISK"]

# Replay for incident response
from lumyn.cli.commands import replay
replay.main(pack_path="decision_01JBQX.zip")
```

## Frequently Asked Questions

### What happens if my policy changes?

Decision Records include `policy_hash` (cryptographic hash of the policy). If you replay a Decision Record with a different policy, Lumyn will detect the mismatch and show you the diff. This prevents silent policy drift during incident investigation.

### Can I replay decisions from months ago?

Yes, if you store the Decision Record and pin your Lumyn version. The `inputs_digest` captures the request state, and `policy_hash` captures the policy state. Replay is deterministic as long as the engine version matches.

### How do Decision Records handle memory/learning?

Lumyn's v1.3+ includes memory-driven reason codes like `FAILURE_MEMORY_SIMILAR_BLOCK`. When you label a past decision as SUCCESS or FAILURE using `lumyn learn`, future similar decisions will include memory similarity scores and reason codes in their Decision Records.

### Are Decision Records GDPR-compliant?

Decision Records support redaction profiles. You can store decisions with PII removed while keeping the verdict, reason codes, and policy_hash intact for audit purposes. See the `context.redaction` field in the v1 schema.

### How large are Decision Records?

Typical size: 2-10 KB per decision depending on policy complexity and memory hits. For high-throughput systems, store only essential fields or use a retention policy (e.g., keep full records for 90 days, keep verdict+reasons forever).

## Next Steps

- **[Quickstart Guide](/docs/quickstart)** - Implement Decision Records in 5 minutes
- **[v1 Semantics](/docs/v1_semantics)** - Deep dive into verdict types and evaluation order
- **[Replay Guarantees](/docs/replay-guarantees)** - Understand deterministic replay contracts
- **[Memory Integration](/docs/memory)** - Add learning feedback loops to your decision system
