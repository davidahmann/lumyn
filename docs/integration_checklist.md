# Integration Checklist (copy/paste)

Use this before you roll Lumyn into a real write-path.

## 1) Install + sanity

- `pip install lumyn`
- `lumyn --help`

## 2) Create/repair workspace

- `lumyn doctor --fix`

## 3) Pick a policy pack (optional)

Default pack: `policies/lumyn-support.v0.yml` (refunds + ticket operations).

To switch packs locally:
- `lumyn init --workspace .lumyn-account --policy-template policies/packs/lumyn-account.v0.yml`
- `lumyn init --workspace .lumyn-billing --policy-template policies/packs/lumyn-billing.v0.yml`

Validate:
- `lumyn policy validate --workspace .lumyn-account`

## 4) Validate your request template against schema

Example (replace `request.json` with your file):

`python - <<'PY'\nimport json\nfrom jsonschema import Draft202012Validator\nfrom lumyn.schemas.loaders import load_json_schema\nschema = load_json_schema('schemas/decision_request.v0.schema.json')\nreq = json.load(open('request.json', encoding='utf-8'))\nDraft202012Validator(schema).validate(req)\nprint('ok')\nPY`

## 5) Run a dry-run decision and store it

- `lumyn decide --in request.json --pretty`
- Capture `decision_id`, then: `lumyn show <decision_id>`

## 6) Incident flow (export + replay verify)

- `lumyn export <decision_id> --pack --out decision_pack.zip`
- `lumyn replay decision_pack.zip`

## 7) Experience Memory (compounding)

- `lumyn demo --story`

## 8) Service mode (optional)

- `lumyn serve --dry-run`
- `lumyn serve`

Optional request signing:
- Set `LUMYN_SIGNING_SECRET`
- Send `X-Lumyn-Signature: sha256:<hmac(body_bytes)>` over the exact bytes you send
