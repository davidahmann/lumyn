# Integration Checklist (copy/paste)

Use this before you roll Lumyn into a real write-path.

## 1) Install + sanity

- `pip install lumyn`
- `lumyn init` (creates `.lumyn/`)

## 2) Validate your request template (v1)

Ensure your app generates valid `decision_request.v1` JSON.

`python - <<'PY'\nimport json\nfrom jsonschema import Draft202012Validator\nfrom lumyn.schemas.loaders import load_json_schema\nschema = load_json_schema('schemas/decision_request.v1.schema.json')\nreq = json.load(open('request.json', encoding='utf-8'))\nDraft202012Validator(schema).validate(req)\nprint('ok')\nPY`

## 3) Dry-run locally

- `lumyn decide request.json --pretty`

## 4) Incident Readiness

- Verify you can allow/block via `policy.yml` edits.
- Verify `lumyn replay` works on exported zips.

## 5) Service mode (optional)

- `lumyn serve`
- `curl -X POST http://localhost:8000/v1/decide ...`
