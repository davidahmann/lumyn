---
title: What is a Decision Record?
description: "A Decision Record is a durable receipt for gated actions: verdict, stable reason codes, and replayable digests."
---

# What is a Decision Record?

A **Decision Record** is a durable, replayable receipt for a gated action in production AI.

It captures:

- A **verdict**: `ALLOW | ABSTAIN | ESCALATE | DENY`
- **Stable reason codes** (machine strings you can alert on)
- **Digests** that make the decision reproducible

Why it matters: when something goes wrong (fraud, policy violation, unsafe output), you need evidence that
is better than screenshots and best-effort logs.

## Decision Records vs. logs

Logs are helpful, but they often fail audits and incident response because they’re:

- Incomplete (missing inputs or context)
- Non-deterministic (can’t reproduce the same outcome)
- Not normalized (hard to alert or trend on)

A Decision Record is intentionally structured so you can replay, debug, and build workflows around it.

## Next steps

- [Quickstart](/docs/quickstart)
- [v1 semantics](/docs/v1_semantics)
- [Replay guarantees](/docs/replay-guarantees)
