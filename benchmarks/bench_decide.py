from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

from lumyn.core.decide import LumynConfig, decide


def _request(i: int) -> dict[str, object]:
    digest = "sha256:" + f"{i:064x}"[-64:]
    return {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {
            "type": "support.refund",
            "intent": "Refund duplicate charge for order 82731",
            "amount": {"value": 42.5, "currency": "USD"},
            "tags": ["duplicate_charge"],
        },
        "evidence": {"ticket_id": "ZD-1001", "order_id": "82731", "customer_id": "C-9"},
        "context": {"mode": "digest_only", "digest": digest},
    }


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = int((len(values_sorted) - 1) * p)
    return values_sorted[k]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--db", type=Path, default=Path(".lumyn/bench.db"))
    args = parser.parse_args()

    cfg = LumynConfig(policy_path="policies/lumyn-support.v0.yml", store_path=args.db)

    timings: list[float] = []
    for i in range(args.n):
        start = time.perf_counter()
        decide(_request(i), config=cfg)
        timings.append(time.perf_counter() - start)

    ms = [t * 1000.0 for t in timings]
    print(f"n={len(ms)} db={args.db}")
    print(f"p50_ms={_percentile(ms, 0.50):.2f}")
    print(f"p95_ms={_percentile(ms, 0.95):.2f}")
    print(f"mean_ms={statistics.mean(ms):.2f}")


if __name__ == "__main__":
    main()
