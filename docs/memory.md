# Lumyn Memory (BEM Integration)

Lumyn V1.3 introduces **Institutional Memory**, powered by Bidirectional Experience Memory (BEM) concepts. This allows Lumyn to learn from past decisions and outcomes, enabling "Self-Healing" policies and "Pre-Cognition" risk avoidance.

## Core Concepts

### 1. Experiences
Every decision made by Lumyn can be turned into an **Experience** by attaching an **Outcome** (Success or Failure).
- **Success**: The transaction was legitimate (e.g., no chargeback).
- **Failure**: The transaction was fraudulent or problematic (e.g., chargeback received).

### 2. Projection Layer
Lumyn projects every request into a high-dimensional vector space (embedding) using a semantic model. This places similar requests close to each other, even if their raw data differs slightly.

### 3. Memory Store
Experiences are stored in a local vector database (`lancedb`). This allows for sub-millisecond similarity search.

### 4. Consensus Engine
When a new request arrives, Lumyn consults both its **Heuristic Rules** (Policy) and its **Memory**. A Consensus Engine arbitrates between them:
- **Pre-Cognition**: If the Policy says `ALLOW`, but Memory sees a high similarity to a past **Failure**, the Consensus Engine overrides the verdict to `ABSTAIN` (Block), preventing a repeat mistake.
- **Self-Healing**: If the Policy says `ESCALATE` (manual review), but Memory sees a high similarity to past **Successes**, the Consensus Engine can override to `ALLOW` (Auto-Approve).

## Usage

### Enabling Memory
Memory is enabled by default in V1.3. It requires key dependencies (`lancedb`, `fastembed`, `pandas`).

### Teaching Lumyn
Use the `lumyn learn` CLI command to feed outcomes back into the system.

```bash
# Mark a past decision as a FAILURE (e.g., after receiving a chargeback)
lumyn learn <decision_id> --outcome FAILURE --severity 5

# Mark a past decision as a SUCCESS (e.g., after successful delivery)
lumyn learn <decision_id> --outcome SUCCESS
```

### Monitoring Memory
Decisions overridden by Memory include stable reason codes:
- `FAILURE_MEMORY_SIMILAR_BLOCK` (Memory blocks an otherwise-`ALLOW`)
- `SUCCESS_MEMORY_SIMILAR_ALLOW` (Memory allows an otherwise-`ESCALATE`)

Dynamic evidence (scores and top matches) lives under:
- `risk_signals.failure_similarity`
- `risk_signals.success_similarity`

## Uncertainty Score

The `risk_signals.uncertainty_score` field indicates how novel a request pattern is:

- **Low uncertainty (< 0.3)**: Lumyn has seen many similar patterns before. High confidence in the verdict.
- **High uncertainty (> 0.7)**: This is a novel pattern with little or no historical precedent. Consider escalating for human review.

**Formula**: `uncertainty = 1.0 - max(success_similarity, failure_similarity)`

This means:
- If a request closely matches known successes or failures, uncertainty is low.
- If a request matches nothing in memory, uncertainty approaches 1.0.

Use this in your escalation logic:
Use `risk_signals.uncertainty_score` in your application routing (outside of policy evaluation) to
decide whether to send a decision to human review.
