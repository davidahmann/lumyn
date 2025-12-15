# Quickstart (no keys, no Docker)

Goal: gate a real write-path action with `decide()`, persist a **Decision Record**, and export/replay it under incident pressure.

Lumyn is local-first in v0: it stores decisions in SQLite under `.lumyn/` by default.

## Requirements

- Python `>=3.11`
- Optional: `curl` + `jq` (used in examples below)

## 1) Install

From PyPI:

- `pip install lumyn`
- Service mode: `pip install lumyn[service]`

From source (contributors):

- `uv sync --dev`
- `uv run pytest -q`

## 2) Create/repair a local workspace

This creates:
- `.lumyn/lumyn.db` (SQLite store)
- `.lumyn/policy.yml` (starter policy)

`lumyn doctor --fix`

## 3) Fastest “aha”: compounding in seconds

This prints a short narrative:
1) decide
2) label as failure
3) decide again and show similarity influence

`lumyn demo --story`

## 4) Make a decision from a request file

Create a request file:

`cat > request.json <<'JSON'\n{\n  \"schema_version\": \"decision_request.v0\",\n  \"request_id\": \"req_123\",\n  \"subject\": {\"type\": \"service\", \"id\": \"support-agent\", \"tenant_id\": \"acme\"},\n  \"action\": {\n    \"type\": \"support.refund\",\n    \"intent\": \"Refund duplicate charge for order 82731\",\n    \"amount\": {\"value\": 12.0, \"currency\": \"USD\"},\n    \"tags\": [\"duplicate_charge\"]\n  },\n  \"evidence\": {\n    \"ticket_id\": \"ZD-1001\",\n    \"order_id\": \"82731\",\n    \"customer_id\": \"C-9\",\n    \"customer_age_days\": 180,\n    \"previous_refund_count_90d\": 0,\n    \"chargeback_risk\": 0.05,\n    \"payment_instrument_risk\": \"low\"\n  },\n  \"context\": {\"mode\": \"digest_only\", \"digest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}\n}\nJSON`

Decide (writes the Decision Record to SQLite and prints it):

`lumyn decide --in request.json --out decision.json --pretty`

Extract the `decision_id`:

`python - <<'PY'\nimport json\nprint(json.load(open('decision.json', encoding='utf-8'))['decision_id'])\nPY`

## 5) Show / explain / export / replay (incident workflow)

Show:

`lumyn show <decision_id>`

Explain (paste-ready):

`lumyn explain <decision_id> --markdown`

Export a decision pack ZIP (record + request + policy snapshot) and verify it offline:

`lumyn export <decision_id> --pack --out decision_pack.zip`

`lumyn replay decision_pack.zip --markdown`

## 6) Label an outcome (Experience Memory)

When you learn the real-world result:

`lumyn label <decision_id> --label failure --summary "Refund caused chargeback"`

This appends an event and writes a memory item that can influence future decisions via similarity.

## 7) Try another policy pack (account / billing)

Create a separate workspace with a different policy template:

`lumyn init --workspace .lumyn-account --policy-template policies/packs/lumyn-account.v0.yml`

`lumyn init --workspace .lumyn-billing --policy-template policies/packs/lumyn-billing.v0.yml`

Validate:

`lumyn policy validate --workspace .lumyn-account`

## 8) Service mode (optional)

Start the API:

`lumyn serve --dry-run`

`lumyn serve --host 127.0.0.1 --port 8000`

Call it:

`curl -sS -X POST http://127.0.0.1:8000/v0/decide -H 'content-type: application/json' --data-binary @request.json | jq .`

v1 preview endpoint (same engine; v1 request/record schema wrapper):

`jq '.schema_version=\"decision_request.v1\"' request.json > request_v1.json`

`curl -sS -X POST http://127.0.0.1:8000/v1/decide -H 'content-type: application/json' --data-binary @request_v1.json | jq .`

Optional request signing:
- Set `LUMYN_SIGNING_SECRET`
- Send `X-Lumyn-Signature: sha256:<hmac(body_bytes)>` over the exact bytes you send

Example (sign a file you send via `--data-binary @file`):

`export LUMYN_SIGNING_SECRET='dev-signing-key'`  # pragma: allowlist secret

`export SIG="$(python - <<'PY'\nimport hmac, hashlib\nsecret = b'dev-signing-key'  # pragma: allowlist secret\nbody = open('request.json','rb').read()\nprint('sha256:' + hmac.new(secret, body, hashlib.sha256).hexdigest())\nPY\n)"`

`curl -sS -X POST http://127.0.0.1:8000/v0/decide -H 'content-type: application/json' -H \"X-Lumyn-Signature: $SIG\" --data-binary @request.json | jq .`

## Next steps

- `docs/integration_checklist.md`: production copy/paste checklist
- `docs/architecture.md`: architecture and end-to-end flow diagrams
