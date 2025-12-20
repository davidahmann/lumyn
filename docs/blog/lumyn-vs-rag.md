---
title: "Lumyn vs RAG: When to Use Each"
description: "RAG retrieves context for LLMs; Lumyn enforces deterministic policies for gated actions. Learn when to use retrieval vs policy-driven decisions for production AI systems."
keywords: RAG, retrieval augmented generation, policy engine, decision gateway, AI governance, vector search vs rules
---

# Lumyn vs RAG: When to Use Each

**RAG (Retrieval-Augmented Generation) retrieves context to enhance LLM responses. Lumyn enforces deterministic policies to gate high-risk actions.** They solve fundamentally different problems: RAG makes LLMs smarter by providing relevant information; Lumyn makes AI systems **accountable** by enforcing governance rules with replayable evidence.

## The Core Difference

| Aspect | RAG | Lumyn |
|--------|-----|-------|
| **Purpose** | Enhance LLM responses with retrieved context | Enforce policy decisions for gated actions |
| **Output** | Natural language response | Structured verdict (ALLOW/DENY/ESCALATE/ABSTAIN) |
| **Determinism** | Non-deterministic (LLM variability) | Deterministic (same inputs → same verdict) |
| **Use Case** | Q&A, chatbots, content generation | Fraud prevention, compliance, access control |
| **Evidence** | Retrieved documents (for context) | Decision Records (for audit) |

## What is RAG?

Retrieval-Augmented Generation enhances Large Language Models by retrieving relevant documents before generating responses:

```python
# Typical RAG flow
def rag_query(question: str) -> str:
    # 1. Retrieve relevant context
    docs = vector_db.similarity_search(question, top_k=5)
    
    # 2. Build prompt with context
    prompt = f"Context: {docs}\n\nQuestion: {question}\n\nAnswer:"
    
    # 3. Generate response
    response = llm.complete(prompt)
    return response

# Example
answer = rag_query("What is the refund policy?")
# Returns: "Based on our policy docs, refunds are allowed within 30 days..."
```

**RAG is great for**:
- Customer support chatbots
- Document Q&A systems
- Knowledge base search
- Content generation with factual grounding

**RAG is NOT designed for**:
- Enforcing compliance rules
- Making reproducible decisions
- Gating high-risk actions
- Audit trails for regulators

## What is Lumyn?

Lumyn is a **deterministic policy engine** that evaluates structured rules and returns machine-stable verdicts:

```python
# Lumyn policy-driven decision
from lumyn import decide, LumynConfig

record = decide(
    request={
        "subject": {"type": "user", "id": "usr_123"},
        "action": {"type": "refund", "amount": {"value": 500, "currency": "USD"}},
        "context": {"mode": "inline", "inline": {...}, "digest": "sha256:..."}
    },
    config=LumynConfig(policy_path="policy.yml")
)

print(record["verdict"])       # "DENY" (not prose explanation)
print(record["reason_codes"])  # ["CHARGEBACK_RISK_BLOCK"]
```

**Lumyn is great for**:
- Fraud prevention gates
- Compliance-driven decisions
- Access control with audit trails
- High-value transaction approvals

**Lumyn is NOT designed for**:
- Natural language Q&A
- Content generation
- Conversational AI
- Open-ended reasoning

## When RAG Fails for Decision-Making

### Problem 1: Non-Deterministic Outputs

RAG depends on LLMs, which are probabilistic:

```python
# Same question, different answers
response1 = rag_query("Should we approve this \$5000 refund?")
# "Yes, based on customer history..."

response2 = rag_query("Should we approve this \$5000 refund?")  
# "I'd suggest reviewing it first because..."

# Different every time! Can't build alerts or dashboards on this.
```

**With Lumyn**:
```python
record = decide(refund_request, config=cfg)
# Always returns: {"verdict": "ESCALATE", "reason_codes": ["REFUND_OVER_ESCALATION_LIMIT"]}
# Same inputs → same verdict. Deterministic.
```

### Problem 2: No Machine-Stable Reason Codes

RAG returns natural language explanations:

```
"This refund seems risky because the customer has a high chargeback rate,
but they've also been a loyal customer for 3 years, so it's complicated..."
```

You can't:
- Alert on "chargeback rate > threshold"
- Query SQL for "top deny reasons"
- Build compliance dashboards

**With Lumyn**:
```json
{
  "verdict": "DENY",
  "reason_codes": ["CHARGEBACK_RISK_BLOCK"],
  "risk_signals": {
    "chargeback_probability": 0.87
  }
}
```

Now you can: `SELECT COUNT(*) WHERE reason_codes CONTAINS 'CHARGEBACK_RISK_BLOCK'`

### Problem 3: No Replay Guarantees

RAG has no concept of deterministic replay. You can't prove "this is why we denied it last month."

**With Lumyn**:
```bash
$ lumyn export 01JBQX... --pack --out decision.zip
$ lumyn replay decision.zip

# Reproduces exact verdict + reasons from 6 months ago
verdict: DENY
reason_codes: CHARGEBACK_RISK_BLOCK
policy_hash: sha256:a4f2c8...
```

Perfect for audits, incident response, and compliance.

## When to Use Both Together

RAG and Lumyn are **complementary** for complex AI systems:

### Pattern 1: RAG for Context, Lumyn for Gating

```python
# 1. Use RAG to gather context
customer_history = rag_query(f"Summarize customer {user_id} refund history")

# 2. Use Lumyn to enforce policy
record = decide(
    request={
        "subject": {"id": user_id},
        "action": {"type": "refund", "amount": {"value": 500, "currency": "USD"}},
        "context": {
            "mode": "inline",
            "inline": {"customer_summary": customer_history},  # RAG output as context
            "digest": "sha256:..."
        }
    },
    config=LumynConfig(policy_path="policy.yml")
)

if record["verdict"] == "DENY":
    # Use RAG to explain to customer
    explanation = rag_query(
        f"Explain why refund was denied due to {record['reason_codes']}"
    )
    return {"verdict": "DENY", "explanation": explanation}
```

**Result**: RAG provides conversational explanations, Lumyn provides governance.

### Pattern 2: Lumyn Memory as RAG Context

```python
# Lumyn stores labeled decisions in memory
lumyn label 01JBQX... --label failure --summary "Fraudulent refund from compromised account"

# Later: Use memory as RAG context
similar_failures = vector_db.search(
    query=current_request,
    filter={"label": "failure"},
    top_k=3
)

# Show operator: "This request is similar to these past fraud cases..."
```

**Result**: Lumyn's memory becomes retrieval corpus for human context.

## Architecture Comparison

### RAG Architecture

```
User Question
    ↓
[1. Embed Query] (OpenAI/Cohere)
    ↓
[2. Vector Search] (Pinecone/Weaviate/Chroma)
    ↓
[3. Retrieve Top-K Docs]
    ↓
[4. Build Prompt with Context]
    ↓
[5. LLM Generate Response] (GPT-4/Claude)
    ↓
Natural Language Answer
```

**Characteristics**:
- Probabilistic at every step
- Output varies between runs
- No structured verdict
- Optimized for relevance, not compliance

### Lumyn Architecture

```
Decision Request
    ↓
[1. Normalize Request] (Deterministic)
    ↓
[2. Evaluate Policy Rules] (YAML-based)
    ↓
[3. Check Memory Similarity] (Optional)
    ↓
[4. Arbitrate Consensus] (Rules + Memory)
    ↓
Decision Record (verdict, reason_codes, inputs_digest)
```

**Characteristics**:
- Deterministic replay with inputs_digest
- Structured output (JSON schema)
- Machine-stable reason codes
- Optimized for governance, not conversation

## Cost Comparison

### RAG Costs
```
Query: "Should we approve this refund?"

OpenAI embedding: $0.0001 per query
Vector DB: $0.001 per query (managed service)
LLM generation (GPT-4): $0.03 per query

Total: ~$0.031 per decision
```

At 1M decisions/month: **$31,000/month**

### Lumyn Costs
```
Policy evaluation: In-memory (free)
Memory search: SQLite/local vector DB (free)
Decision Record storage: 10 KB × $0.000001 (S3)

Total: ~$0.00001 per decision
```

At 1M decisions/month: **$10/month** (3,100x cheaper)

**Why**: Lumyn avoids LLM API calls for every decision. Rules are deterministic and run locally.

## Real-World Use Case: Refund Approval

### RAG Approach
```python
prompt = f"""
Customer requested \$500 refund.
Customer history: {rag_retrieve(user_id)}
Policy docs: {rag_retrieve("refund policy")}

Should we approve? Consider chargeback risk, customer loyalty, amount.
"""

decision = llm.complete(prompt)
# "I recommend escalating because while the customer is loyal,
#  the amount is high and there's moderate chargeback risk..."
```

**Problems**:
- ❌ Not deterministic (different answer each time)
- ❌ Can't alert on "chargeback risk" (it's in prose)
- ❌ Can't replay for audit
- ❌ Expensive ($0.03 per decision)

### Lumyn Approach
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
      reason_codes: ["REFUND_OVER_ESCALATION_LIMIT"]
      
  - id: R_CHARGEBACK_RISK
    stage: HARD_BLOCKS
    if:
      action_type: "refund"
      evidence.chargeback_probability: { gt: 0.8 }
    then:
      verdict: DENY
      reason_codes: ["CHARGEBACK_RISK_BLOCK"]
```

```python
record = decide(refund_request, config=cfg)
# {"verdict": "ESCALATE", "reason_codes": ["REFUND_OVER_ESCALATION_LIMIT"]}
```

**Benefits**:
- ✅ Deterministic (same inputs → same verdict)
- ✅ Machine-stable codes (can alert/query)
- ✅ Replayable for audits
- ✅ Cheap ($0.00001 per decision)

## Hybrid: Best of Both Worlds

```python
def approve_refund(request):
    # 1. Lumyn: Enforce policy
    record = decide(request, config=LumynConfig(policy_path="policy.yml"))
    
    # 2. If escalated, use RAG for rich context
    if record["verdict"] == "ESCALATE":
        # Retrieve similar cases for human review
        similar = rag_query(
            f"Find similar refund cases with reason: {record['reason_codes']}"
        )
        return {
            "status": "REQUIRES_REVIEW",
            "verdict": record["verdict"],
            "reason_codes": record["reason_codes"],
            "similar_cases": similar,  # RAG adds human context
            "decision_id": record["decision_id"]
        }
    
    # 3. If denied, use RAG to explain to customer
    elif record["verdict"] == "DENY":
        explanation = rag_query(
            f"Explain to customer why refund denied for: {record['reason_codes']}"
        )
        return {
            "status": "DENIED",
            "reason_codes": record["reason_codes"],
            "customer_message": explanation  # RAG generates friendly message
        }
    
    return {"status": "APPROVED"}
```

**Result**: 
- **Lumyn** handles governance (deterministic, auditable, cheap)
- **RAG** handles communication (conversational, contextual, expensive only when needed)

## Frequently Asked Questions

### Can I use RAG to implement a policy engine?

Not recommended. RAG depends on LLMs which are:
- **Non-deterministic** (different answers each time)
- **Expensive** (~$0.03 per query vs $0.00001)
- **Unstructured output** (can't build dashboards/alerts)

Use RAG for **context retrieval**, not **decision enforcement**.

### Can Lumyn replace RAG for customer support?

No. Lumyn returns structured verdicts (`ALLOW/DENY`), not conversational answers. For Q&A chatbots, use RAG. For gating actions (refunds, access control), use Lumyn.

### Does Lumyn support vector search like RAG?

Yes, via **Memory**. Lumyn can search past labeled decisions for similarity, but it's used to **influence policy**, not generate prose. Memory similarity appears as a reason code (e.g., `FAILURE_MEMORY_SIMILAR_BLOCK`).

### What if I need both explainability and governance?

Use **both**:
1. Lumyn for the verdict (deterministic, auditable)
2. RAG to generate customer-facing explanations from reason codes

See "Hybrid: Best of Both Worlds" above.

### Can I use Lumyn's memory as a RAG corpus?

Yes! Lumyn's memory stores labeled decisions which can be retrieved as context for RAG queries. Example: "Show me similar past fraud cases for this refund request."

## Next Steps

- **[What is a Decision Record?](/blog/what-is-a-decision-record)** - Understand Lumyn's structured output
- **[Lumyn Memory](/docs/memory)** - Learn about similarity-based learning (Lumyn's answer to retrieval)
- **[Quickstart](/docs/quickstart)** - Implement your first policy-driven decision
- **[Reason Codes Are A Contract](/blog/reason-codes-are-a-contract)** - Why machine-stable codes matter
