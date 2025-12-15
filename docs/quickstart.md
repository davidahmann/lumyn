# Quickstart

Goal: gate a real write-path action with `decide()`, persist a **Decision Record**, and export/replay it under incident pressure.

## Requirements

- Python `>=3.11`
- Optional: `curl` + `jq`

## 1) Install

- `pip install lumyn`

## 2) Create a workspace

This creates `.lumyn/lumyn.db` and the default `policy.yml` (v1):

`lumyn init`

## 3) Make a decision

Create a `request.json` file (v1 schema):

```json
{
  "schema_version": "decision_request.v1",
  "request_id": "req_123",
  "subject": {"type": "service", "id": "support-agent", "tenant_id": "acme"},
  "action": {
    "type": "support.refund",
    "intent": "Refund duplicate charge",
    "amount": {"value": 12.0, "currency": "USD"}
  },
  "evidence": {
    "ticket_id": "ZD-1001",
    "payment_instrument_risk": "low"
  },
  "context": {"mode": "digest_only", "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
}
```

Run CLI decision:

`lumyn decide request.json --pretty`

> [!TIP]
> Open a second terminal and run `lumyn monitor` to see a live "Matrix-style" feed of decisions as they happen!

## 4) Incident flow (show / explain / export / replay)

Get the `decision_id` from the output above, then:

- `lumyn show <decision_id>`
- `lumyn explain <decision_id> --markdown`
- `lumyn export <decision_id> --pack --out incident.zip`
- `lumyn replay incident.zip`

## 5) Service mode (optional)

`lumyn serve`

Call with curl:

`curl -sS -X POST http://127.0.0.1:8000/v1/decide -H 'content-type: application/json' --data-binary @request.json | jq .`
