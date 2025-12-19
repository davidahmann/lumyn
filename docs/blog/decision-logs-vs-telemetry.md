---
title: Decision logs vs telemetry
description: Telemetry explains systems; Decision Records explain outcomes. You need both, but for different jobs.
---

# Decision logs vs telemetry

Telemetry tells you what the system did (latency, errors, traces). It is essential, but it does not answer a
different question operators always ask:

> Why was this action allowed (or denied)?

Decision Records are the missing layer:

- Telemetry: “the request went here, it took 230ms”
- Decision Record: “the gateway returned `DENY` because `FAILURE_MEMORY_SIMILAR_BLOCK`”

## When telemetry fails

In gated AI actions (refunds, approvals, publishing, data access), the failure mode is often *not* an exception.
It’s a bad decision with no replayable evidence.

## Next steps

- [What is a Decision Record?](/blog/what-is-a-decision-record)
- [Replay guarantees](/docs/replay-guarantees)
