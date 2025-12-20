---
title: "Lumyn vs Fine-Tuning: When to Use Each"
description: "Fine-tuning adjusts model weights for better outputs; Lumyn enforces deterministic governance without retraining. Learn when to tune your LLM vs when to gate its decisions."
keywords: fine-tuning, LLM training, policy engine, model governance, deterministic AI, supervised learning vs rules
---

# Lumyn vs Fine-Tuning: When to Use Each

**Fine-tuning adapts LLM weights to improve response quality. Lumyn enforces deterministic policies without touching the model.** They address orthogonal concerns: fine-tuning makes your LLM better at its task; Lumyn makes

 your AI system **governable** regardless of what LLM you use.

## The Core Difference

| Aspect | Fine-Tuning | Lumyn |
|--------|-------------|-------|
| **What it changes** | Model weights (neural network parameters) | Policy rules (YAML configuration) |
| **When it runs** | Training time (hours/days) | Decision time (milliseconds) |
| **Purpose** | Improve LLM output quality | Enforce governance rules |
| **Determinism** | Still probabilistic (LLMs vary) | Deterministic (same inputs → same verdict) |
| **Cost** | $100-$10,000 per training run | $0 (local evaluation) |
| **Update speed** | Days (retrain + deploy) | Seconds (update YAML) |

## What is Fine-Tuning?

Fine-tuning takes a pre-trained LLM and adjusts its weights on domain-specific data:

```python
from openai import OpenAI

# Fine-tune GPT-4 on customer support examples
client = OpenAI()
client.fine_tuning.jobs.create(
    training_file="file-abc123",  # Your examples
    model="gpt-4-0613",
    hyperparameters={"n_epochs": 3}
)
# Cost: ~$100-$500
# Time: 2-8 hours
```

**Fine-tuning is great for**:
- Domain-specific language (medical, legal, technical)
- Consistent tone/style
- Task-specific formats (structured outputs)
- Reducing prompt engineering

**Fine-tuning does NOT provide**:
- Deterministic decisions
- Audit trails
- Governance rules
- Replay guarantees

## What is Lumyn?

Lumyn evaluates structured policy rules to gate actions, without any model training:

```yaml
# policy.yml - update in seconds, no retraining
rules:
  - id: R_HIGH_AMOUNT
    if:
      amount_usd: { gt: 1000 }
    then:
      verdict: ESCALATE
      reason_codes: ["AMOUNT_OVER_THRESHOLD"]
```

```python
from lumyn import decide, LumynConfig

record = decide(request, config=LumynConfig(policy_path="policy.yml"))
# Decision in milliseconds, deterministic, auditable
```

**Lumyn is great for**:
- Compliance-driven gating
- Fraud prevention
- Access control
- Audit requirements

**Lumyn does NOT**:
- Improve LLM output quality
- Change model behavior
- Require training data

## When Fine-Tuning Fails for Governance

### Problem 1: Still Non-Deterministic

Even after fine-tuning, LLMs are probabilistic:

```python
# Fine-tuned model for refund approvals
response1 = fine_tuned_llm("Approve \$500 refund for user_123?")
# "Approved" (temperature=0.7)

response2 = fine_tuned_llm("Approve \$500 refund for user_123?")
# "I recommend escalating due to amount" (same temp, different output!)
```

You **cannot**:
- Replay the exact decision for audits
- Alert on specific policy violations
- Guarantee same verdict for same inputs

**With Lumyn**:
```python
record = decide(refund_request, config=cfg)
# Always: {"verdict": "ESCALATE", "reason_codes": ["REFUND_OVER_ESCALATION_LIMIT"]}
# Deterministic replay with inputs_digest
```

### Problem 2: Slow Policy Updates

Fine-tuning requires full retraining cycle:

```
1. Collect new training examples (days)
2. Fine-tune model ($100-$500, 2-8 hours)
3. Evaluate on test set (hours)
4. Deploy new model (CI/CD pipeline)
5. Monitor for regressions

Total: 1-2 weeks minimum
```

**With Lumyn**:
```yaml
# Edit policy.yml
rules:
  - id: R_NEW_FRAUD_BLOCK
    if:
      evidence.risk_score: { gt: 0.9 }
    then:
      verdict: DENY
      reason_codes: ["HIGH_FRAUD_RISK"]
```

```bash
$ git commit -m "Add fraud rule" policy.yml
$ git push
# Live in production in seconds
```

### Problem 3: No Structured Governance

Fine-tuned models still return natural language, not machine-stable codes:

```python
fine_tuned_output = "This request seems risky due to high chargeback probability,
                      but the customer has been loyal for 3 years, so I'd suggest 
                      manual review before deciding."
```

**Problems**:
- Can't query SQL for "top deny reasons"
- Can't alert on "chargeback risk" threshold
- No compliance dashboard

**With Lumyn**:
```json
{
  "verdict": "ESCALATE",
  "reason_codes": ["CHARGEBACK_RISK_HIGH", "MANUAL_REVIEW_REQUIRED"],
  "risk_signals": {"chargeback_probability": 0.87}
}
```

Now: `SELECT COUNT(*) WHERE 'CHARGEBACK_RISK_HIGH' = ANY(reason_codes)`

## When to Use Both Together

Fine-tuning and Lumyn are **complementary** in production AI systems:

### Pattern 1: Fine-Tuned LLM → Lumyn Gate

```python
# 1. Fine-tuned LLM generates risk assessment
risk_assessment = fine_tuned_llm(
    f"Analyze refund risk for customer {user_id}"
)
# Returns: {"risk_score": 0.87, "factors": ["high_chargeback_history"]}

# 2. Lumyn enforces policy on LLM output
record = decide(
    request={
        "action": {"type": "refund", "amount": {"value": 500, "currency": "USD"}},
        "evidence": {"risk_score": risk_assessment["risk_score"]},
        "context": {"mode": "inline", "inline": risk_assessment, "digest": "sha256:..."}
    },
    config=LumynConfig(policy_path="policy.yml")
)

if record["verdict"] == "DENY":
    # Policy overrides LLM's "maybe approve" tendency
    return {"status": "BLOCKED", "reason_codes": record["reason_codes"]}
```

**Result**: LLM provides nuanced risk analysis (via fine-tuning), Lumyn enforces hard rules (governance).

### Pattern 2: Lumyn Memory Informs Fine-Tuning Data

```python
# 1. Lumyn collects labeled decisions over time
$ lumyn label 01JBQX... --label failure --summary "Fraudulent refund"
$ lumyn label 01JBQY... --label success --summary "Legitimate refund"

# 2. Export Lumyn memory as fine-tuning examples
decisions = export_decision_records(label="failure", limit=1000)

training_data = []
for decision in decisions:
    training_data.append({
        "messages": [
            {"role": "user", "content": f"Analyze: {decision['request']}"},
            {"role": "assistant", "content": f"DENY - {decision['reason_codes']}"}
        ]
    })

# 3. Fine-tune on Lumyn's curated dataset
client.fine_tuning.jobs.create(training_file=training_data, model="gpt-4")
```

**Result**: Lumyn's governance decisions become training signal for LLM.

## Cost Comparison

### Fine-Tuning Costs (OpenAI GPT-4)
```
Training: $0.0080 per 1K tokens
- 100K training examples × 500 tokens avg = 50M tokens
- Cost: $0.0080 × 50,000 = $400 per training run

Inference: $0.03 per 1K tokens (same as base model)
- 1M decisions × 200 tokens avg = 200M tokens
- Cost: $0.03 × 200,000 = $6,000/month

Total first month: $6,400
```

### Lumyn Costs
```
Policy evaluation: In-memory (free)
Memory search: Local vector DB (free)
Decision storage: 10 KB × $0.000001 (S3)

1M decisions: ~$10/month (640x cheaper)
```

**Key insight**: Fine-tuning adds training cost BUT doesn't reduce inference cost. Lumyn avoids LLM calls entirely for governance.

## Speed Comparison

### Fine-Tuning Latency
```
Request → LLM API → Wait for response → Parse output
Latency: 500ms - 3 seconds (depending on model size)
```

### Lumyn Latency
```
Request → Evaluate policy rules → Return verdict
Latency: 1ms - 50ms (in-process, no API calls)
```

**30-3000x faster** for gated decisions.

## When Fine-Tuning Makes Sense

Use fine-tuning when you need to:

1. **Improve LLM output quality**
   ```python
   # Fine-tune for domain-specific language
   base_llm("Explain hemoptysis") → "Coughing up blood"
   fine_tuned_llm("Explain hemoptysis") → "Expectoration of blood from respiratory tract,
                                             often indicating pulmonary hemorrhage..."
   ```

2. **Consistent formatting**
   ```python
   # Fine-tune for structured JSON output
   base_llm("Extract entities") → "The person is John, age 30..."
   fine_tuned_llm("Extract entities") → {"name": "John", "age": 30}
   ```

3. **Reduce prompt tokens**
   ```python
   # Base model needs 500-token prompt
   base_llm(long_prompt + query)
   
   # Fine-tuned model internalizes instructions
   fine_tuned_llm(query)  # Shorter prompt = cheaper
   ```

## When Lumyn Makes Sense

Use Lumyn when you need to:

1. **Enforce compliance rules**
   ```yaml
   rules:
     - id: GDPR_RETENTION
       if:
         data_age_days: { gt: 365 }
       then:
         verdict: DENY
         reason_codes: ["GDPR_RETENTION_VIOLATION"]
   ```

2. **Deterministic replay for audits**
   ```bash
   $ lumyn replay decision_6months_ago.zip
   verdict: DENY
   reason_codes: REFUND_OVER_ESCALATION_LIMIT
   policy_hash: sha256:a4f2c8...
   # Exact reproduction for regulators
   ```

3. **Fast policy updates**
   ```yaml
   # Update policy in seconds
   rules:
     - id: NEW_FRAUD_RULE
       if:
         evidence.device_fingerprint: { in: ["banned_device_1", "banned_device_2"] }
       then:
         verdict: DENY
   ```

4. **Machine-stable reason codes**
   ```sql
   -- Dashboard query
   SELECT reason_code, COUNT(*)
   FROM decision_records
   WHERE verdict = 'DENY'
   GROUP BY reason_code;
   ```

## Hybrid Architecture

Production systems often use **both**:

```
┌─────────────────────────────────────────────┐
│ Request (e.g., refund approval)             │
└──────────────────┬──────────────────────────┘
                   ↓
    ┌──────────────────────────┐
    │ Fine-Tuned Risk Model    │
    │ (GPT-4 fine-tuned on     │
    │  past fraud cases)       │
    └──────────┬───────────────┘
               ↓
       risk_score: 0.87
               ↓
    ┌──────────────────────────┐
    │ Lumyn Policy Engine      │
    │ RULE: if risk > 0.8,     │
    │ verdict: DENY            │
    └──────────┬───────────────┘
               ↓
    Decision Record
    {verdict: "DENY",
     reason_codes: ["FRAUD_RISK_HIGH"]}
```

**Why this works**:
- **Fine-tuning** makes the risk model better (domain-specific learning)
- **Lumyn** enforces governance rules on top (deterministic gating)

## Real-World Example: Content Moderation

### Fine-Tuning Approach
```python
# Fine-tune GPT-4 on moderation examples
moderation_llm = fine_tune(
    model="gpt-4",
    examples=[
        {"input": "hate speech example", "output": "BLOCK: violates policy 3.2"},
        {"input": "borderline case", "output": "ALLOW: within guidelines"},
    ]
)

# Use in production
decision = moderation_llm(user_content)
# Problem: Still probabilistic, no replay, no structured codes
```

### Lumyn Approach
```yaml
# policy.yml
rules:
  - id: HATE_SPEECH_BLOCK
    if:
      evidence.hate_speech_score: { gt: 0.9 }
    then:
      verdict: DENY
      reason_codes: ["HATE_SPEECH_DETECTED"]
      
  - id: BORDERLINE_ESCALATE
    if:
      evidence.hate_speech_score: { between: [0.7, 0.9] }
    then:
      verdict: ESCALATE
      reason_codes: ["BORDERLINE_CONTENT_MANUAL_REVIEW"]
```

```python
# In production
hate_score = fine_tuned_classifier(user_content)  # Fine-tuned for better accuracy

record = decide(
    request={"action": {"type": "publish"}, "evidence": {"hate_speech_score": hate_score}},
    config=LumynConfig(policy_path="policy.yml")
)
# Deterministic gate based on LLM's score
```

### Hybrid: Best of Both
- **Fine-tuning** improves hate speech classifier accuracy
- **Lumyn** enforces consistent thresholds with audit trail

## Frequently Asked Questions

### Can fine-tuning replace Lumyn for compliance?

No. Fine-tuning improves LLM quality but doesn't provide:
- Deterministic replay
- Machine-stable reason codes
- Audit trails
- Fast policy updates (seconds vs days)

### Can I fine-tune on Lumyn's decision data?

Yes! Export Lumyn's labeled decisions as training examples:
```python
failures = get_decisions(label="failure", limit=1000)
training_data = format_for_finetuning(failures)
fine_tune(model="gpt-4", data=training_data)
```

This creates a feedback loop: Lumyn governance → LLM improvement.

### Does Lumyn work with fine-tuned models?

Yes. Lumyn is model-agnostic. Use fine-tuned LLMs to generate risk scores/classifications, then gate them with Lumyn policies.

### What if I can't afford fine-tuning?

Use Lumyn alone. Policy rules don't require training:
```yaml
rules:
  - if: {amount_usd: {gt: 1000}}
    then: {verdict: ESCALATE}
```

No LLM needed, no training cost.

### Can I use fine-tuning for memory instead of Lumyn's similarity search?

No. Fine-tuning bakes patterns into weights (slow updates). Lumyn's memory is append-only and queryable in real-time:
```bash
$ lumyn label 01JBQX... --label failure
# Immediately affects next decision (no retraining)
```

## Next Steps

- **[Lumyn Memory](/docs/memory)** - Real-time learning without fine-tuning
- **[Lumyn vs RAG](/blog/lumyn-vs-rag)** - Another model enhancement technique vs governance
- **[Replay Guarantees](/docs/replay-guarantees)** - Why determinism matters for audits
- **[Quickstart](/docs/quickstart)** - Implement policy-driven gates in 5 minutes
