from __future__ import annotations

from lumyn import LumynConfig, decide


def main() -> None:
    cfg = LumynConfig(policy_path="policies/lumyn-support.v0.yml", store_path=".lumyn/lumyn.db")
    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
        "action": {
            "type": "support.refund",
            "intent": "Refund duplicate charge for order 82731",
            "amount": {"value": 42.5, "currency": "USD"},
            "tags": ["duplicate_charge"],
        },
        "evidence": {"ticket_id": "ZD-1001", "order_id": "82731", "customer_id": "C-9"},
        "context": {
            "mode": "digest_only",
            "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        },
    }

    record = decide(request, config=cfg)
    print(record["decision_id"], record["verdict"], record["reason_codes"])


if __name__ == "__main__":
    main()
