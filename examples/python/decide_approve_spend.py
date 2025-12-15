from __future__ import annotations

from lumyn import LumynConfig, decide


def main() -> None:
    cfg = LumynConfig(
        policy_path="policies/packs/lumyn-billing.v0.yml", store_path=".lumyn/lumyn.db"
    )
    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "service", "id": "billing-bot", "tenant_id": "acme"},
        "action": {
            "type": "billing.approve_spend",
            "intent": "Approve invoice INV-1001",
            "amount": {"value": 85.0, "currency": "USD"},
        },
        "evidence": {
            "invoice_id": "INV-1001",
            "vendor_id": "V-12",
            "requested_by": "alice@acme.com",
        },
        "context": {
            "mode": "digest_only",
            "digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        },
    }

    record = decide(request, config=cfg)
    print(record["decision_id"], record["verdict"], record["reason_codes"])


if __name__ == "__main__":
    main()
