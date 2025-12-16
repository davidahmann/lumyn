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
Decisions influenced by Memory will have specific reason codes:
- `High similarity (0.95) to failure pattern <id>`
- `High similarity (0.98) to approved pattern <id>`

And the `risk_signals` block in the decision record will contain `failure_similarity` scores.
