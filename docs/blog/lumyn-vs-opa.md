---
title: "Lumyn vs Open Policy Agent (OPA): When to Use Each"
description: "OPA enforces authorization policies; Lumyn enforces decision policies with memory and audit trails. Learn when to use each for governance, compliance, and AI systems."
keywords: OPA, Open Policy Agent, policy engine, decision gateway, authorization vs decisions, Rego vs YAML
---

# Lumyn vs Open Policy Agent (OPA): When to Use Each

**Open Policy Agent (OPA) decouples authorization logic from application code. Lumyn decouples decision logic with memory, replay, and AI-specific features.** Both are policy engines, but OPA focuses on **"can this happen?"** (authorization) while Lumyn focuses on **"should this happen?"** (decision governance with learning).

## The Core Difference

| Aspect | OPA | Lumyn |
|--------|-----|-------|
| **Primary Use Case** | Authorization (RBAC, ABAC, network policies) | Decision governance (fraud, compliance, gating) |
| **Policy Language** | Rego (logic programming) | YAML (declarative rules) |
| **Memory/Learning** | No built-in memory | Yes (similarity-based learning from outcomes) |
| **Decision Records** | No (just allow/deny) | Yes (structured with reason codes, replay) |
| **Replay Guarantees** | No cryptographic digest | Yes (inputs_digest, policy_hash) |
| **Target Domain** | Kubernetes, microservices, API gateways | AI systems, fraud prevention, high-risk decisions |

## What is OPA?

Open Policy Agent is a **general-purpose policy engine** that evaluates Rego policies to authorize requests:

```rego
# policy.rego
package authz

default allow = false

allow {
    input.method == "GET"
    input.user.role == "admin"
}

allow {
    input.method == "GET"
    input.path[0] == "public"
}
```

```python
# Query OPA
import requests

response = requests.post("http://localhost:8181/v1/data/authz/allow", json={
    "input": {
        "method": "GET",
        "user": {"role": "user"},
        "path": ["public", "docs"]
    }
})

print(response.json()["result"])  # true
```

**OPA is great for**:
- Kubernetes admission control
- API authorization
- Network policy enforcement
- Microservice authorization

**OPA does NOT provide**:
- Memory of past decisions
- Structured reason codes
- Decision replay with cryptographic proof
- Learning from outcomes

## What is Lumyn?

Lumyn is a **decision policy engine** that enforces governance rules AND learns from labeled outcomes:

```yaml
# policy.yml
rules:
  - id: R_HIGH_AMOUNT
    stage: ESCALATIONS
    if:
      amount_usd: { gt: 1000 }
    then:
      verdict: ESCALATE
      reason_codes: ["AMOUNT_OVER_ESCALATION_LIMIT"]
```

```python
from lumyn import decide, LumynConfig

record = decide(
    request={
        "action": {"type": "refund", "amount": {"value": 1500, "currency": "USD"}},
        "context": {"mode": "inline", "inline": {...}, "digest": "sha256:..."}
    },
    config=LumynConfig(policy_path="policy.yml")
)

print(record["verdict"])       # "ESCALATE"
print(record["reason_codes"])  # ["AMOUNT_OVER_ESCALATION_LIMIT"]
print(record["decision_id"])   # "01JBQX..."
```

**Lumyn is great for**:
- AI decision gating
- Fraud prevention
- Compliance workflows
- Learning from past failures

**Lumyn does NOT replace**:
- Kubernetes admission control
- Generic API authorization
- Network policies

## When OPA Falls Short for Decision Governance

### Problem 1: No Decision Records

OPA returns binary allow/deny without structured context:

```rego
# OPA policy
package refund

deny[reason] {
    input.amount > 1000
    reason := "Amount too high"
}
```

```json
// OPA response
{
  "result": ["Amount too high"]
}
```

**Problems**:
- No decision_id for tracking
- No cryptographic digest for replay
- No machine-stable reason codes (string matching is fragile)
- Can't query: `SELECT COUNT(*) WHERE reason_code = 'AMOUNT_LIMIT'`

**With Lumyn**:
```json
{
  "decision_id": "01JBQX...",
  "verdict": "DENY",
  "reason_codes": ["AMOUNT_OVER_LIMIT"],
  "determinism": {
    "inputs_digest": "sha256:a4f2c8...",
    "policy_hash": "sha256:b3e5d9..."
  }
}
```

Now you can:
- Track decisions over time
- Replay for audits
- Build dashboards on reason_codes

### Problem 2: No Memory or Learning

OPA evaluates policies in isolation (stateless):

```rego
# OPA has no concept of "this looks like past fraud cases"
package fraud

deny[reason] {
    input.risk_score > 0.8
    reason := "High risk score"
}
```

**With Lumyn**:
```bash
# Label past decisions
$ lumyn label 01JBQX... --label failure --summary "Fraudulent refund from compromised account"

# Next decision checks similarity to past failures
$ lumyn decide refund_request.json
```

```json
{
  "verdict": "DENY",
  "reason_codes": ["FAILURE_MEMORY_SIMILAR_BLOCK"],
  "risk_signals": {
    "failure_similarity_score": 0.93,
    "failure_similarity_top_k": ["01JBQX...", "01JBQY..."]
  }
}
```

Lumyn **learns** from labeled outcomes without retraining.

### Problem 3: No Replay Guarantees

OPA doesn't capture the decision context for replay:

```bash
# OPA: Can't reproduce "why did we deny in November?"
# No inputs_digest, no policy_hash
```

**With Lumyn**:
```bash
$ lumyn export 01JBQX... --pack --out decision.zip
$ lumyn replay decision.zip

# Reproduces exact verdict from 6 months ago
verdict: DENY
reason_codes: CHARGEBACK_RISK_BLOCK
policy_hash: sha256:a4f2c8...
inputs_digest: sha256:b3e5d9...
```

Perfect for compliance audits.

## When to Use Both Together

OPA and Lumyn can work in tandem for different layers:

### Pattern 1: OPA for Authorization, Lumyn for Decision

```python
# 1. OPA: Check if user is authorized
opa_response = requests.post("http://opa:8181/v1/data/authz/allow_refund", json={
    "input": {"user": user_id, "role": user_role}
})

if not opa_response.json()["result"]:
    return {"error": "UNAUTHORIZED"}

# 2. Lumyn: Check if refund should be approved
record = decide(
    request={"action": {"type": "refund", "amount": amount}, ...},
    config=LumynConfig(policy_path="policy.yml")
)

if record["verdict"] == "DENY":
    return {"error": "POLICY_VIOLATION", "reason_codes": record["reason_codes"]}
```

**Result**:
- **OPA** handles "can this user initiate refunds?" (RBAC)
- **Lumyn** handles "should this specific refund be approved?" (governance)

### Pattern 2: Lumyn Decision Records as OPA Input

```rego
# OPA policy referencing Lumyn decisions
package elevated_access

allow {
    # Check past Lumyn decisions for this user
    count([d | d := data.lumyn_decisions[_]; d.subject.id == input.user; d.verdict == "DENY"]) < 3
}
```

```python
# Feed Lumyn decisions to OPA
recent_decisions = get_recent_lumyn_decisions(user_id, limit=10)
opa_data = {"lumyn_decisions": recent_decisions}

# OPA uses Lumyn history for authorization
```

**Result**: Lumyn's decision history informs OPA's authorization logic.

## Architecture Comparison

### OPA Architecture

```
Authorization Request
    ↓
[OPA Engine] ← Rego Policies
    ↓
Boolean (allow/deny) + optional reasons
```

**Characteristics**:
- Stateless evaluation
- Logic programming (Rego)
- General-purpose authorization
- No built-in decision tracking

### Lumyn Architecture

```
Decision Request
    ↓
[Policy Rules] ← YAML Policy
    ↓
[Memory Similarity] ← Labeled Past Decisions
    ↓
[Consensus Arbitration]
    ↓
Decision Record (verdict, reason_codes, inputs_digest)
```

**Characteristics**:
- Stateful memory
- Learning from outcomes
- Decision-specific (high-risk actions)
- Built-in audit trail

## Policy Language Comparison

### OPA Rego
```rego
package refund_policy

import future.keywords.if

default verdict := "DENY"

verdict := "ALLOW" if {
    input.amount < 100
    input.user.trusted == true
}

verdict := "ESCALATE" if {
    input.amount >= 100
    input.amount < 1000
}

verdict := "DENY" if {
    input.risk_score > 0.8
}
```

**Characteristics**:
- Logic programming (Prolog-like)
- Flexible, powerful
- Steeper learning curve
- No built-in stages or precedence

### Lumyn YAML
```yaml
rules:
  - id: R_LOW_AMOUNT_ALLOW
    stage: TRUST_PATHS
    if:
      amount_usd: { lt: 100 }
      user.trusted: { eq: true }
    then:
      verdict: ALLOW
      reason_codes: ["SMALL_AMOUNT_TRUSTED_USER"]
  
  - id: R_MID_AMOUNT_ESCALATE
    stage: ESCALATIONS
    if:
      amount_usd: { between: [100, 1000] }
    then:
      verdict: ESCALATE
      reason_codes: ["AMOUNT_OVER_ESCALATION_LIMIT"]
  
  - id: R_HIGH_RISK_DENY
    stage: HARD_BLOCKS
    if:
      evidence.risk_score: { gt: 0.8 }
    then:
      verdict: DENY
      reason_codes: ["HIGH_FRAUD_RISK"]
```

**Characteristics**:
- Declarative YAML
- Explicit stages and precedence
- Easier for non-programmers
- Decision-optimized (reason_codes, queries, obligations)

## Real-World Use Case: Refund Approval System

### OPA Approach
```rego
package refund

import future.keywords.if

deny[reason] if {
    input.amount > 1000
    reason := "amount_exceeds_limit"
}

deny[reason] if {
    input.user.chargeback_rate > 0.5
    reason := "high_chargeback_risk"
}
```

```python
response = requests.post("http://opa:8181/v1/data/refund", json={"input": refund_request})
result = response.json()["result"]

if result.get("deny"):
    print(f"Denied: {result['deny']}")
else:
    print("Allowed")
```

**Limitations**:
- No decision_id for tracking
- No memory of past fraud patterns
- No replay for audits
- Reason strings (not machine-stable codes)

### Lumyn Approach
```yaml
# policy.yml
defaults:
  mode: enforce
  default_verdict: ESCALATE

rules:
  - id: R_AMOUNT_LIMIT
    stage: ESCALATIONS
    if:
      amount_usd: { gt: 1000 }
    then:
      verdict: ESCALATE
      reason_codes: ["AMOUNT_OVER_LIMIT"]
  
  - id: R_CHARGEBACK_BLOCK
    stage: HARD_BLOCKS
    if:
      evidence.chargeback_rate: { gt: 0.5 }
    then:
      verdict: DENY
      reason_codes: ["HIGH_CHARGEBACK_RISK"]
```

```python
record = decide(refund_request, config=LumynConfig(policy_path="policy.yml"))

print(f"Decision ID: {record['decision_id']}")
print(f"Verdict: {record['verdict']}")
print(f"Reason Codes: {record['reason_codes']}")

# Label outcome for learning
if fraud_confirmed:
    os.system(f"lumyn label {record['decision_id']} --label failure --summary 'Confirmed fraud'")
```

**Benefits**:
- Decision tracking (decision_id)
- Memory learning (labeled outcomes)
- Replay for audits (inputs_digest)
- Machine-stable reason codes

## When OPA Makes Sense

Use OPA when you need:

1. **Kubernetes Admission Control**
   ```rego
   package kubernetes.admission
   
   deny[reason] {
       input.request.kind.kind == "Pod"
       not input.request.object.spec.securityContext.runAsNonRoot
       reason := "Pods must run as non-root"
   }
   ```

2. **API Authorization**
   ```rego
   package api.authz
   
   allow {
       input.method == "GET"
       input.user.role == "viewer"
   }
   ```

3. **General-Purpose Policy Enforcement**
   ```rego
   package terraform
   
   deny[reason] {
       input.resource.type == "aws_s3_bucket"
       not input.resource.change.after.versioning[0].enabled
       reason := "S3 versioning required"
   }
   ```

## When Lumyn Makes Sense

Use Lumyn when you need:

1. **Decision Governance with Audit Trails**
   ```yaml
   rules:
     - id: GDPR_RETENTION
       if: {data_retention_days: {gt: 365}, user_region: {eq: "EU"}}
       then: {verdict: DENY, reason_codes: ["GDPR_VIOLATION"]}
   ```

2. **Learning from Outcomes**
   ```bash
   $ lumyn label 01JBQX... --label failure --summary "Confirmed fraud case"
   # Future decisions learn from this pattern
   ```

3. **Cryptographic Replay**
   ```bash
   $ lumyn replay decision_from_2023.zip
   # Exact reproduction for regulators
   ```

4. **AI Decision Gating**
   ```yaml
   rules:
     - id: LLM_OUTPUT_CHECK
       if: {evidence.toxicity_score: {gt: 0.7}}
       then: {verdict: DENY, reason_codes: ["TOXIC_CONTENT_BLOCK"]}
   ```

## Hybrid Architecture: OPA + Lumyn

```
Incoming Request
    ↓
┌─────────────────────┐
│ OPA Authorization   │ ← "Can user X do this?" (RBAC/ABAC)
│ Result: allow/deny  │
└──────────┬──────────┘
           ↓ (if allowed)
┌─────────────────────┐
│ Lumyn Decision Gate │ ← "Should we approve this specific action?"
│ Result: ALLOW/DENY/ │   (with memory, reason codes, replay)
│ ESCALATE/ABSTAIN    │
└──────────┬──────────┘
           ↓
Execute Action (if ALLOW)
```

**Why this works**:
- **OPA** handles identity and permissions (who can act)
- **Lumyn** handles governance and risk (what actions are safe)

## Frequently Asked Questions

### Can OPA replace Lumyn for fraud prevention?

Not recommended. OPA lacks:
- Memory/learning from past fraud
- Structured decision records
- Replay guarantees
- Reason code stability

Use OPA for authorization, Lumyn for fraud gating.

### Can Lumyn replace OPA for Kubernetes policies?

No. Lumyn is optimized for high-risk decisions with audit requirements, not generic admission control. Use OPA for K8s.

### Can I use OPA policies as input to Lumyn?

Yes. OPA can compute evidence that Lumyn policies evaluate:
```python
opa_result = query_opa(request)
record = decide(
    request={"evidence": {"opa_score": opa_result}, ...},
    config=cfg
)
```

### Does Lumyn support Rego?

No. Lumyn uses declarative YAML for easier authoring and decision-optimized features (stages, reason codes, memory).

### When should I use OPA AND Lumyn together?

When you have layered governance:
- **Layer 1 (OPA)**: "Is user authorized to request refunds?" (RBAC)
- **Layer 2 (Lumyn)**: "Should this specific $5000 refund be approved?" (risk-based gating)

## Next Steps

- **[What is a Decision Record?](/blog/what-is-a-decision-record)** - Understand Lumyn's structured output
- **[Lumyn Memory](/docs/memory)** - Learn about similarity-based learning
- **[Replay Guarantees](/docs/replay-guarantees)** - Why cryptographic replay matters
- **[Quickstart](/docs/quickstart)** - Implement policy-driven gates in 5 minutes
