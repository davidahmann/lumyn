# Contributing

Thanks for helping improve Lumyn.

## What to contribute

- Bug reports with a minimal reproducer and a DecisionRecord/DecisionRequest example.
- New policy rule types or starter policy packs (with vectors).
- Golden vectors that lock down edge cases and prevent determinism regressions.
- Docs and integration examples for real workflows (refunds/tickets/write-path gates).

## Development setup

Prereqs: Python 3.11+ and `uv`.

```bash
uv sync --dev
uv run pre-commit install
```

Run checks:

```bash
uv run pre-commit run --all-files
uv run pytest
```

## Contracts and determinism rules

Before changing schemas/policies/evaluator behavior, read:
- `SPECS_SCHEMAS.md`

Expectations:
- v0 schemas are additive-only (breaking changes require `*.v1`)
- reason codes are stable strings
- golden vectors must be updated for any behavior change

