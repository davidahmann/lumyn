# Quickstart (15 minutes)

Goal: emit a **Decision Record** for a real action (refund / ticket update), store it locally, and replay it by `decision_id`.

## 1) Install + checks

From the repo:

`uv sync --dev`

Verify:

`uv run pytest -q`

## 2) Initialize a local workspace

`uv run lumyn init`

This creates:
- `.lumyn/lumyn.db` (SQLite store)
- `.lumyn/policy.yml` (starter policy)

## 3) Run the demo

`uv run lumyn demo --pretty`

You’ll get a JSON array of `DecisionRecord` objects.

Fastest “aha” (compounding):

`uv run lumyn demo --story`

## 4) Decide from a request file

Use the curl-ready request example:

`uv run lumyn decide --in examples/curl/decision_request_refund.json --pretty`

Capture the `decision_id` from the output.

Tip (recommended): set `request_id` in your `DecisionRequest` so retries are idempotent.

## 5) Show / explain / export

`uv run lumyn show <decision_id>`

`uv run lumyn explain <decision_id>`

`uv run lumyn export <decision_id> --out decision_record.json`

Create an incident-ready decision pack and validate it:

`uv run lumyn export <decision_id> --pack --out decision_pack.zip`

`uv run lumyn replay decision_pack.zip`

## 6) Label an outcome (Experience Memory)

When you learn the real-world result:

`uv run lumyn label <decision_id> --label failure --summary "Refund caused chargeback"`

This appends a decision event and writes a memory item that can influence similarity on future decisions.

## 6.1) Try another pack (account / billing)

Switch the workspace policy:

`cp policies/packs/lumyn-account.v0.yml .lumyn/policy.yml`

`uv run lumyn decide --in examples/curl/decision_request_change_email.json --pretty`

Switch again:

`cp policies/packs/lumyn-billing.v0.yml .lumyn/policy.yml`

`uv run lumyn decide --in examples/curl/decision_request_approve_spend.json --pretty`

## 7) Service mode (optional)

Run the API:

`uv run lumyn serve`

Call it:

`curl -sS -X POST http://127.0.0.1:8000/v0/decide -H 'content-type: application/json' --data-binary @examples/curl/decision_request_refund.json | jq .`

Optional request signing (service mode):
- Set `LUMYN_SIGNING_SECRET`
- Send `X-Lumyn-Signature: sha256:<hmac(body)>` where `body` is the **exact bytes** you send.

Example (sign a file you send via `--data-binary @file`):

`export LUMYN_SIGNING_SECRET='dev-signing-key'`  # pragma: allowlist secret

`export SIG="$(python - <<'PY'\nimport hmac, hashlib\nsecret = b'dev-signing-key'  # pragma: allowlist secret\nbody = open('examples/curl/decision_request_refund.json','rb').read()\nprint('sha256:' + hmac.new(secret, body, hashlib.sha256).hexdigest())\nPY\n)"`

`curl -sS -X POST http://127.0.0.1:8000/v0/decide -H 'content-type: application/json' -H "X-Lumyn-Signature: $SIG" --data-binary @examples/curl/decision_request_refund.json`
