from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import typer
import yaml
from jsonschema import Draft202012Validator

from lumyn.engine.normalize import normalize_request
from lumyn.policy.loader import compute_policy_hash
from lumyn.policy.validate import validate_policy_or_raise
from lumyn.records.emit import compute_inputs_digest
from lumyn.schemas.loaders import load_json_schema

from ..util import die

app = typer.Typer(help="Validate and summarize a Lumyn decision pack (ZIP).")


def _zip_read_json(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    try:
        raw = zf.read(name).decode("utf-8")
    except KeyError:
        die(f"missing {name} in pack")
    data = json.loads(raw)
    if not isinstance(data, dict):
        die(f"{name} must be a JSON object")
    return data


def _zip_read_text(zf: zipfile.ZipFile, name: str) -> str:
    try:
        return zf.read(name).decode("utf-8")
    except KeyError:
        die(f"missing {name} in pack")


@app.callback(invoke_without_command=True)
def main(
    pack_path: Path = typer.Argument(..., help="Decision pack ZIP path."),
    *,
    markdown: bool = typer.Option(False, "--markdown", help="Emit markdown summary."),
) -> None:
    if not pack_path.exists():
        die(f"pack not found: {pack_path}")
    if pack_path.suffix.lower() != ".zip":
        die("pack_path must be a .zip file")

    request_schema = load_json_schema("schemas/decision_request.v0.schema.json")
    record_schema = load_json_schema("schemas/decision_record.v0.schema.json")
    policy_schema_path = "schemas/policy.v0.schema.json"
    reason_codes_path = "schemas/reason_codes.v0.json"

    with zipfile.ZipFile(pack_path) as zf:
        record = _zip_read_json(zf, "decision_record.json")
        request = _zip_read_json(zf, "request.json")
        policy_text = _zip_read_text(zf, "policy.yml")

    Draft202012Validator(record_schema).validate(record)
    Draft202012Validator(request_schema).validate(request)

    policy_obj = yaml.safe_load(policy_text)
    if not isinstance(policy_obj, dict):
        die("policy.yml did not parse to an object")
    validate_policy_or_raise(
        policy_obj, policy_schema_path=policy_schema_path, reason_codes_path=reason_codes_path
    )
    policy_hash = compute_policy_hash(policy_obj)

    raw_record_policy = record.get("policy")
    record_policy: dict[str, Any]
    if isinstance(raw_record_policy, dict):
        record_policy = raw_record_policy
    else:
        record_policy = {}

    expected_hash = record_policy.get("policy_hash")
    if expected_hash != policy_hash:
        die(f"policy_hash mismatch: record={expected_hash} computed={policy_hash}")

    normalized = normalize_request(request)
    computed_inputs_digest = compute_inputs_digest(request, normalized=normalized)
    raw_determinism = record.get("determinism")
    determinism: dict[str, Any]
    if isinstance(raw_determinism, dict):
        determinism = raw_determinism
    else:
        determinism = {}
    if determinism.get("inputs_digest") != computed_inputs_digest:
        die(
            "inputs_digest mismatch: "
            f"record={determinism.get('inputs_digest')} computed={computed_inputs_digest}"
        )

    decision_id = record.get("decision_id")
    verdict = record.get("verdict")
    raw_reason_codes = record.get("reason_codes")
    reason_codes: list[object]
    if isinstance(raw_reason_codes, list):
        reason_codes = raw_reason_codes
    else:
        reason_codes = []

    raw_context = request.get("context")
    context: dict[str, Any]
    if isinstance(raw_context, dict):
        context = raw_context
    else:
        context = {}

    if markdown:
        typer.echo(f"# Lumyn decision `{decision_id}`")
        typer.echo(f"- verdict: `{verdict}`")
        typer.echo(f"- reason_codes: `{', '.join([str(x) for x in reason_codes]) or '(none)'}`")
        typer.echo(f"- policy_hash: `{policy_hash}`")
        typer.echo(f"- context_digest: `{context.get('digest')}`")
        typer.echo(f"- inputs_digest: `{computed_inputs_digest}`")
    else:
        typer.echo("ok")
        typer.echo(f"decision_id: {decision_id}")
        typer.echo(f"verdict: {verdict}")
        typer.echo(f"policy_hash: {policy_hash}")
        typer.echo(f"context_digest: {context.get('digest')}")
        typer.echo(f"inputs_digest: {computed_inputs_digest}")
