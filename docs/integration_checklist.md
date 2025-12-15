# Integration Checklist (copy/paste)

Use this before you roll Lumyn into a real write-path.

## 1) Install + sanity

- `uv sync --dev`
- `uv run pytest -q`

## 2) Create/repair workspace

- `uv run lumyn doctor --fix`

## 3) Pick a policy pack (optional)

Default pack: `policies/lumyn-support.v0.yml` (refunds + ticket operations).

To switch packs locally:
- `cp policies/packs/lumyn-account.v0.yml .lumyn/policy.yml`
- `cp policies/packs/lumyn-billing.v0.yml .lumyn/policy.yml`

Validate:
- `uv run lumyn policy validate`

## 4) Validate your request template against schema

Example (replace `request.json` with your file):

`uv run python - <<'PY'\nimport json\nfrom jsonschema import Draft202012Validator\nschema = json.load(open('schemas/decision_request.v0.schema.json'))\nreq = json.load(open('request.json'))\nDraft202012Validator(schema).validate(req)\nprint('ok')\nPY`

## 5) Run a dry-run decision and store it

- `uv run lumyn decide --in examples/curl/decision_request_refund.json --pretty`
- Capture `decision_id`, then: `uv run lumyn show <decision_id>`

## 6) Incident flow (export + replay verify)

- `uv run lumyn export <decision_id> --pack --out decision_pack.zip`
- `uv run lumyn replay decision_pack.zip`

## 7) Experience Memory (compounding)

- `uv run lumyn demo --story`

## 8) Service mode (optional)

- `uv run lumyn serve --dry-run`
- `uv run lumyn serve`

Optional request signing:
- Set `LUMYN_SIGNING_SECRET`
- Send `X-Lumyn-Signature: sha256:<hmac(body_bytes)>` over the exact bytes you send
