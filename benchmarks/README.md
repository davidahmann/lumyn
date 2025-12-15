# Benchmarks (local)

These benchmarks are **not** run in CI. They are intended to provide a repeatable local baseline.

## Decide baseline

Run:

`uv run python benchmarks/bench_decide.py --n 200`

Notes:
- Uses local SQLite at `.lumyn/bench.db`
- Uses the starter policy `policies/lumyn-support.v0.yml`
- Prints rough p50/p95 timings (wall clock)
