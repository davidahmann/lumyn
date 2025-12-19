---
title: "AI incident response: replay decisions"
description: Treat every incident like a ticket with evidence. Replay the decision, label outcomes, and re-run deterministically.
---

# AI incident response: replay decisions

When an AI-powered workflow causes an incident, teams often fall back to guesswork:
screenshots, partial logs, and “maybe the prompt changed”.

Lumyn’s incident workflow is simpler:

1. **Record** every gated action as a Decision Record.
2. **Replay** deterministically to reproduce verdict + reasons.
3. **Label** outcomes as append-only events (no silent mutations).
4. **Re-run** the same request to confirm the fix actually changed behavior.

## Why replay matters

If you can’t replay the decision, you can’t confidently answer:

- What policy fired?
- Which memory items were similar?
- Which reason code drove the verdict?

## Next steps

- [Quickstart](/docs/quickstart)
- [Replay guarantees](/docs/replay-guarantees)
