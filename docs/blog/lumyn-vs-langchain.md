---
title: "Lumyn vs LangChain: When to Use Each"
description: "LangChain orchestrates LLM workflows; Lumyn enforces deterministic governance. Learn when to use orchestration vs policy-driven decision gates for production AI."
keywords: LangChain, LLM orchestration, policy engine, decision gateway, AI governance, workflow vs rules
---

# Lumyn vs LangChain: When to Use Each

**LangChain orchestrates complex LLM workflows with chains, agents, and tools. Lumyn enforces deterministic policies for gated actions with audit trails.** They serve different purposes: LangChain builds AI applications by combining LLM capabilities; Lumyn governs AI decisions by enforcing compliance rules.

## The Core Difference

| Aspect | LangChain | Lumyn |
|--------|-----------|-------|
| **Purpose** | Orchestrate LLM workflows | Enforce policy decisions |
| **Output** | LLM-generated content | Structured verdict (ALLOW/DENY/ESCALATE/ABSTAIN) |
| **Determinism** | Non-deterministic (LLMs vary) | Deterministic (same inputs → same verdict) |
| **Use Case** | Chatbots, agents, RAG, summarization | Fraud gates, compliance, access control |
| **Governance** | No built-in audit trail | Decision Records with replay |
| **Update Speed** | Code deployment | Policy update (seconds) |

## What is LangChain?

LangChain is a **framework for building LLM-powered applications** by chaining together components:

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI

# Build a chain
prompt = PromptTemplate(
    input_variables=["product"],
    template="Generate a product description for {product}"
)

chain = LLMChain(llm=OpenAI(), prompt=prompt)
result = chain.run(product="AI-powered refund analyzer")
```

**LangChain is great for**:
- Building LLM applications (chatbots, agents)
- Chaining multiple LLM calls
- RAG (retrieval-augmented generation)
- Tool use (via agents)
- Document processing

**LangChain is NOT designed for**:
- Deterministic decision enforcement
- Audit compliance
- Replay guarantees
- Machine-stable governance

## What is Lumyn?

Lumyn is a **policy engine** that evaluates structured rules and returns deterministic verdicts:

```python
from lumyn import decide, LumynConfig

record = decide(
    request={
        "subject": {"type": "user", "id": "usr_123"},
        "action": {"type": "refund", "amount": {"value": 500, "currency": "USD"}},
        "context": {"mode": "inline", "inline": {...}, "digest": "sha256:..."}
    },
    config=LumynConfig(policy_path="policy.yml")
)

print(record["verdict"])       # "DENY" (deterministic)
print(record["reason_codes"])  # ["CHARGEBACK_RISK_BLOCK"]
```

**Lumyn is great for**:
- Policy-driven gating
- Fraud prevention
- Compliance workflows
- Audit trails

**Lumyn is NOT designed for**:
- LLM orchestration
- Multi-step workflows
- Tool calling / agents
- Content generation

## When LangChain Fails for Governance

### Problem 1: Non-Deterministic Chains

LangChain chains depend on LLMs, which are probabilistic:

```python
# LangChain refund approval chain
from langchain.chains import SequentialChain

chain = SequentialChain(chains=[
    risk_analysis_chain,   # LLM call
    decision_chain,        # Another LLM call
])

result1 = chain.run(refund_request)
# "Approved - low risk customer"

result2 = chain.run(refund_request)  # Same input!
# "Escalate - unclear risk factors"

# Different every time!
```

**With Lumyn**:
```python
record = decide(refund_request, config=cfg)
# Always: {"verdict": "ESCALATE", "reason_codes": ["REFUND_OVER_ESCALATION_LIMIT"]}
# Deterministic replay
```

### Problem 2: No Built-In Audit Trail

LangChain doesn't enforce structured decision records:

```python
# LangChain output
{
  "llm_output": "Based on the analysis, this refund seems risky...",
  "intermediate_steps": [...]
}
```

**Problems**:
- No machine-stable reason codes
- No replay guarantee
- No cryptographic digest
- Can't query for compliance

**With Lumyn**:
```json
{
  "decision_id": "01JBQX...",
  "verdict": "DENY",
  "reason_codes": ["CHARGEBACK_RISK_BLOCK"],
  "determinism": {
    "inputs_digest": "sha256:a4f2c8...",
    "policy_hash": "sha256:b3e5d9..."
  }
}
```

### Problem 3: Slow Policy Changes

LangChain policies are in code:

```python
# Change policy = change Python code
def approve_refund_chain():
    return SequentialChain(
        chains=[
            analyze_risk,
            check_amount_limit,  # New logic requires code change
            make_decision
        ]
    )

# Deploy via CI/CD (minutes/hours)
```

**With Lumyn**:
```yaml
# policy.yml - update in seconds
rules:
  - id: NEW_RULE
    if: {amount_usd: {gt: 250}}
    then: {verdict: ESCALATE}
```

```bash
$ git push
# Live instantly
```

## When to Use Both Together

LangChain and Lumyn are **complementary** for AI systems that need both orchestration and governance:

### Pattern 1: LangChain for Analysis → Lumyn for Gating

```python
from langchain.chains import LLMChain
from lumyn import decide, LumynConfig

# 1. LangChain: Analyze request using multi-step workflow
analysis_chain = LLMChain(
    llm=ChatOpenAI(model="gpt-4"),
    prompt=PromptTemplate(template="Analyze refund risk: {request}")
)
risk_analysis = analysis_chain.run(request=refund_request)
# Returns: {"risk_score": 0.87, "factors": ["high_chargeback_rate"]}

# 2. Lumyn: Enforce governance on LangChain output
record = decide(
    request={
        "action": {"type": "refund", "amount": {"value": 500, "currency": "USD"}},
        "evidence": {"risk_score": risk_analysis["risk_score"]},
        "context": {"mode": "inline", "inline": risk_analysis, "digest": "sha256:..."}
    },
    config=LumynConfig(policy_path="policy.yml")
)

if record["verdict"] == "DENY":
    # Policy blocks risky refund regardless of LangChain's analysis
    return {"status": "BLOCKED", "reason_codes": record["reason_codes"]}
```

**Result**: LangChain provides sophisticated analysis, Lumyn enforces hard governance rules.

### Pattern 2: Lumyn Gates LangChain Agent Actions

```python
from langchain.agents import initialize_agent, Tool

# LangChain agent with tools
tools = [
    Tool(name="approve_refund", func=approve_refund_tool),
    Tool(name="send_email", func=send_email_tool),
]

agent = initialize_agent(tools, llm=ChatOpenAI(model="gpt-4"))

# Intercept tool calls with Lumyn
def gated_tool_call(tool_name, tool_input):
    # 1. Lumyn policy gate
    record = decide(
        request={"action": {"type": tool_name}, "context": {"mode": "inline", "inline": tool_input, "digest": "sha256:..."}},
        config=LumynConfig(policy_path="policy.yml")
    )
    
    # 2. Block if denied
    if record["verdict"] == "DENY":
        raise PolicyViolation(record["reason_codes"])
    
    # 3. Execute tool if allowed
    return execute_tool(tool_name, tool_input)

# Now agent actions are governed by Lumyn policies
```

**Result**: LangChain agent explores solutions, Lumyn enforces safety rails.

## Architecture Comparison

### LangChain Architecture

```
User Request
    ↓
[LLM Chain 1] → Intermediate Result
    ↓
[LLM Chain 2] → Intermediate Result
    ↓
[LLM Chain 3] → Final Output
    ↓
Natural Language Response
```

**Characteristics**:
- Multi-step LLM workflows
- Probabilistic at every step
- Flexible orchestration
- Code-based logic

### Lumyn Architecture

```
Decision Request
    ↓
[Normalize Request]
    ↓
[Evaluate Policy Rules]
    ↓
[Check Memory Similarity]
    ↓
Decision Record (verdict, reason_codes, inputs_digest)
```

**Characteristics**:
- Single-pass evaluation
- Deterministic replay
- Policy-as-code (YAML)
- Governance-optimized

## Cost Comparison

### LangChain Costs (Multi-Step Chain)
```
3-step refund analysis chain:
- Step 1 (risk analysis): $0.03 per query (GPT-4)
- Step 2 (fraud check): $0.03 per query
- Step 3 (final decision): $0.03 per query

Total: $0.09 per decision

At 1M decisions/month: $90,000/month
```

### Lumyn Costs
```
Policy evaluation: In-memory (free)
Memory search: Local vector DB (free)
Decision storage: 10 KB × $0.000001 (S3)

At 1M decisions/month: $10/month (9,000x cheaper)
```

**Key insight**: LangChain requires multiple LLM calls per workflow. Lumyn avoids LLM calls entirely for policy enforcement.

## When LangChain Makes Sense

Use LangChain when building:

1. **Conversational AI**
   ```python
   from langchain.memory import ConversationBufferMemory
   
   memory = ConversationBufferMemory()
   chain = ConversationChain(llm=OpenAI(), memory=memory)
   
   chain.run("Hi, I need help")
   # LangChain manages multi-turn context
   ```

2. **RAG Systems**
   ```python
   from langchain.vectorstores import Chroma
   from langchain.chains import RetrievalQA
   
   qa_chain = RetrievalQA.from_chain_type(
       llm=OpenAI(),
       retriever=Chroma.as_retriever()
   )
   ```

3. **LLM Agents**
   ```python
   from langchain.agents import create_react_agent
   
   agent = create_react_agent(llm, tools, prompt)
   # Agent decides which tools to use
   ```

## When Lumyn Makes Sense

Use Lumyn for:

1. **Policy-Driven Gates**
   ```yaml
   rules:
     - id: GDPR_CHECK
       if: {user_region: {eq: "EU"}, data_retention_days: {gt: 365}}
       then: {verdict: DENY, reason_codes: ["GDPR_VIOLATION"]}
   ```

2. **Compliance Audit Trails**
   ```bash
   $ lumyn export 01JBQX... --pack
   # Decision Record with cryptographic replay
   ```

3. **Fast Policy Updates**
   ```yaml
   # Update live in seconds
   rules:
     - id: EMERGENCY_FRAUD_BLOCK
       if: {evidence.device_id: {in: ["banned_device_123"]}}
       then: {verdict: DENY}
   ```

## Hybrid: Production AI System

```python
from langchain.chains import LLMChain
from lumyn import decide, LumynConfig

class ProductionRefundSystem:
    def __init__(self):
        # LangChain for sophisticated analysis
        self.risk_chain = LLMChain(
            llm=ChatOpenAI(model="gpt-4"),
            prompt=risk_analysis_prompt
        )
        
        # Lumyn for governance
        self.policy_cfg = LumynConfig(policy_path="policy.yml")
    
    def process_refund(self, request):
        # 1. LangChain: Complex risk analysis
        analysis = self.risk_chain.run(request)
        
        # 2. Lumyn: Enforce policy
        record = decide(
            request={
                "action": {"type": "refund", "amount": request["amount"]},
                "evidence": {"llm_risk_score": analysis["risk_score"]},
                "context": {"mode": "inline", "inline": analysis, "digest": "sha256:..."}
            },
            config=self.policy_cfg
        )
        
        # 3. Handle verdict
        if record["verdict"] == "ALLOW":
            return {"status": "APPROVED", "decision_id": record["decision_id"]}
        elif record["verdict"] == "DENY":
            # LangChain: Generate customer explanation
            explanation = self.explanation_chain.run(
                reason_codes=record["reason_codes"]
            )
            return {
                "status": "DENIED",
                "reason_codes": record["reason_codes"],
                "customer_message": explanation
            }
        else:  # ESCALATE
            return {"status": "MANUAL_REVIEW", "decision_id": record["decision_id"]}
```

**Why this works**:
- **LangChain** handles complex analysis + customer communication
- **Lumyn** enforces governance rules + audit compliance

## Real-World Example: Customer Support Bot

### LangChain-Only Approach
```python
from langchain.agents import Tool, AgentExecutor

tools = [
    Tool(name="approve_refund", func=approve_refund),
    Tool(name="issue_credit", func=issue_credit),
]

agent = initialize_agent(tools, llm=ChatOpenAI(model="gpt-4"), verbose=True)

# Agent decides actions
response = agent.run("Customer wants \$500 refund due to defect")
# "I've approved the $500 refund because..."
```

**Problems**:
- Agent might approve $5000 refund (no hard limits)
- No audit trail for compliance
- Can't replay for incident investigation

### Lumyn-Gated Approach
```python
# Wrap LangChain tools with Lumyn gates
def gated_approve_refund(amount):
    # 1. Lumyn policy check
    record = decide(
        request={"action": {"type": "refund", "amount": {"value": amount, "currency": "USD"}}},
        config=LumynConfig(policy_path="policy.yml")
    )
    
    # 2. Block if policy denies
    if record["verdict"] != "ALLOW":
        return f"Cannot approve: {record['reason_codes']}"
    
    # 3. Execute if allowed
    return execute_refund(amount)

tools = [
    Tool(name="approve_refund", func=gated_approve_refund),
]

agent = initialize_agent(tools, llm=ChatOpenAI(model="gpt-4"))
```

**Result**: Agent explores solutions BUT hard governance rules enforced by Lumyn.

## Frequently Asked Questions

### Can LangChain replace Lumyn for compliance?

No. LangChain orchestrates LLM workflows but doesn't provide:
- Deterministic replay
- Machine-stable reason codes
- Cryptographic audit trails
- Policy-as-code (independent of application logic)

### Can I use Lumyn without LangChain?

Yes. Lumyn is standalone. Use it to gate **any** AI decision, whether from LangChain, custom code, or external APIs.

### Can LangChain call Lumyn policies?

Yes. Treat Lumyn as a tool/function:
```python
from langchain.agents import Tool

lumyn_tool = Tool(
    name="check_policy",
    func=lambda req: decide(req, config=cfg),
    description="Check if action is allowed by policy"
)
```

### What if I don't need LLMs for decisions?

Use Lumyn alone. Policies don't require LLMs:
```yaml
rules:
  - if: {amount_usd: {gt: 1000}}
    then: {verdict: ESCALATE}
```

No LangChain needed, no LLM cost.

### Does Lumyn support LangChain chains as evidence?

Yes. LangChain output can be policy input:
```python
chain_output = langchain_chain.run(request)
record = decide(
    request={"evidence": chain_output, ...},
    config=cfg
)
```

## Next Steps

- **[Lumyn vs RAG](/blog/lumyn-vs-rag)** - Another LLM enhancement vs governance comparison
- **[What is a Decision Record?](/blog/what-is-a-decision-record)** - Understand Lumyn's structured output
- **[Quickstart](/docs/quickstart)** - Implement policy-driven gates in 5 minutes
- **[Replay Guarantees](/docs/replay-guarantees)** - Why determinism matters for audits
