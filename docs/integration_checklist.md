# Integration Checklist (copy/paste)

Use this before you roll Lumyn into a real write-path.

## 1) Install + sanity

- `pip install lumyn`
- `lumyn init` (creates `.lumyn/`)

## 2) Validate your request template (v1)

Ensure your app generates valid `decision_request.v1` JSON.

`python - <<'PY'\nimport json\nfrom jsonschema import Draft202012Validator\nfrom lumyn.schemas.loaders import load_json_schema\nschema = load_json_schema('schemas/decision_request.v1.schema.json')\nreq = json.load(open('request.json', encoding='utf-8'))\nDraft202012Validator(schema).validate(req)\nprint('ok')\nPY`

### 2.5) Bind to a Context Record (recommended)

To avoid future rewrites when you add a context primitive (e.g. Fabra), treat `decision_request.v1.context`
as the stable linkage point:

- Set `context.mode: "reference"`
- Set `context.ref.kind: "fabra.context_record.v1"` (or your own context record kind)
- Set `context.ref.id: <context_id>`
- Set `context.digest: <sha256 digest of the referenced Context Record>`

This gives you an explicit “foreign key” plus a content-addressed digest for replay and audit.

For a durable ticket handle (without coupling Lumyn to any context runtime), also include
`context_ref` on the request with the upstream `context_id` and a `record_hash` (e.g. `sha256:...`),
and paste `context_id + record_hash` into tickets.

Example: `examples/curl/v1/decision_request_refund.json`

## 3) Dry-run locally

- `lumyn decide request.json --pretty`

## 4) Incident Readiness

- Verify you can allow/block via `policy.yml` edits.
- Verify `lumyn replay` works on exported zips.

## 4.5) Voice / Interaction Tracking (optional)

For voice agents (and chat), include an `interaction_ref` on `decision_request.v1` so downstream systems can
carry a stable call/turn reference **without** shipping raw transcripts/audio in Lumyn records.

Important: `interaction_ref.timeline` is an **append-only event log** with a canonical ordering (`index`).
Do not mutate past events; only append new ones, or replay/dispute gets ambiguous.

Voice is also where consent and retention become product-critical fastest—treat `jurisdiction`,
`consent_state`, and `retention` as first-class inputs, and ensure key management/retention policies for any
encrypted journals live in your systems (Lumyn stores refs + digests, not raw audio by default).

## 5) Service mode (optional)

- `lumyn serve`
- `curl -X POST http://localhost:8000/v1/decide ...`
