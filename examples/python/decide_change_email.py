from __future__ import annotations

from lumyn import LumynConfig, decide


def main() -> None:
    cfg = LumynConfig(
        policy_path="policies/packs/lumyn-account.v0.yml", store_path=".lumyn/lumyn.db"
    )
    request = {
        "schema_version": "decision_request.v0",
        "subject": {"type": "user", "id": "user-3", "tenant_id": "acme"},
        "action": {"type": "account.change_email", "intent": "Change account email after reauth"},
        "evidence": {
            "user_id": "user-3",
            "new_email": "new@example.com",
            "verification_method": "reauth",
            "account_takeover_risk": 0.12,
        },
        "context": {
            "mode": "digest_only",
            "digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        },
    }

    record = decide(request, config=cfg)
    print(record["decision_id"], record["verdict"], record["reason_codes"])


if __name__ == "__main__":
    main()
