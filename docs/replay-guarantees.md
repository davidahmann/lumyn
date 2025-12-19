---
title: Replay guarantees
description: What Lumyn can and cannot guarantee when you replay a Decision Record.
---

# Replay guarantees

Lumyn is built around a simple contract: **decisions you can't replay aren't decisions**.

## What is replay?

Replay means evaluating a stored Decision Pack / Decision Record against the same engine semantics and
inputs, producing the same normalized decision output (excluding `decision_id` and `created_at`).

## What is guaranteed (v1)

- If you replay the same stored v1 pack with the same Lumyn version, you get the same verdict and reason codes.
- If your policy and memory snapshot are identical, evaluation is deterministic.
- Reason codes are stable machine strings (no dynamic content).

## What is not guaranteed

- Different Lumyn versions may change behavior (use version pinning when you need strict reproducibility).
- If you depend on external calls during a decision, you must record their outputs (or stub them) to replay.

## Recommended incident workflow

1. Store the Decision Record (and any memory snapshot it depends on).
2. Reproduce via `lumyn replay` to confirm the verdict and reasons.
3. Label outcomes as events (append-only), then re-run the same request to confirm behavior changes.
