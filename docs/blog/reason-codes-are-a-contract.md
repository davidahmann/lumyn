---
title: Reason codes are a contract
description: Stable reason codes unlock alerts, incident workflows, and audits for gated AI actions.
---

# Reason codes are a contract

If you want to operate an AI gate in production, your explanations must be more than human-readable prose.
They must be **machine-stable**.

Lumyn treats reason codes as a public contract:

- Codes are stable strings like `FAILURE_POLICY_VIOLATION`
- No dynamic content inside codes (dynamic evidence belongs elsewhere)
- You can alert, trend, and build workflows on codes

## What this enables

- Reliable dashboards: “top deny reasons this week”
- Incident response: replay a decision and see the exact reasons again
- Audits: consistent evidence instead of ad-hoc explanations

## Next steps

- [v1 semantics](/docs/v1_semantics)
- [Replay guarantees](/docs/replay-guarantees)
