from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import typer
import yaml
from jsonschema import Draft202012Validator

from lumyn.cli.markdown import render_ticket_summary_markdown
from lumyn.engine.normalize import normalize_request
from lumyn.engine.normalize_v1 import compute_inputs_digest_v1, normalize_request_v1
from lumyn.policy.loader import compute_policy_hash
from lumyn.policy.validate import validate_policy_or_raise
from lumyn.records.emit import compute_inputs_digest
from lumyn.schemas.loaders import load_json_schema

from ..util import die

app = typer.Typer(help="Validate and summarize a Lumyn decision pack (ZIP).")

_REQUEST_SCHEMA_BY_VERSION = {
    "decision_request.v0": "schemas/decision_request.v0.schema.json",
    "decision_request.v1": "schemas/decision_request.v1.schema.json",
}
_RECORD_SCHEMA_BY_VERSION = {
    "decision_record.v0": "schemas/decision_record.v0.schema.json",
    "decision_record.v1": "schemas/decision_record.v1.schema.json",
}


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


def _decision_request_v0_equivalent(request: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a v1 request into a v0-equivalent shape for legacy digest verification.

    This is needed because `lumyn convert --to v1` upgrades schema_version fields but does
    not recompute determinism digests (it keeps the original v0 digest).
    """
    schema_version = request.get("schema_version")
    if schema_version == "decision_request.v1":
        out = dict(request)
        out["schema_version"] = "decision_request.v0"
        return out
    return request


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

    with zipfile.ZipFile(pack_path) as zf:
        record = _zip_read_json(zf, "decision_record.json")
        request = _zip_read_json(zf, "request.json")
        policy_text = _zip_read_text(zf, "policy.yml")

    raw_record_schema_version = record.get("schema_version")
    record_schema_version = (
        raw_record_schema_version
        if isinstance(raw_record_schema_version, str)
        else "decision_record.v0"
    )
    record_schema_path = _RECORD_SCHEMA_BY_VERSION.get(
        record_schema_version, "schemas/decision_record.v0.schema.json"
    )
    record_schema = load_json_schema(record_schema_path)

    raw_request_schema_version = request.get("schema_version")
    request_schema_version = (
        raw_request_schema_version
        if isinstance(raw_request_schema_version, str)
        else "decision_request.v0"
    )
    request_schema_path = _REQUEST_SCHEMA_BY_VERSION.get(
        request_schema_version, "schemas/decision_request.v0.schema.json"
    )
    request_schema = load_json_schema(request_schema_path)

    Draft202012Validator(record_schema).validate(record)
    Draft202012Validator(request_schema).validate(request)

    policy_obj = yaml.safe_load(policy_text)
    if not isinstance(policy_obj, dict):
        die("policy.yml did not parse to an object")
    policy_schema_version = policy_obj.get("schema_version")
    policy_schema_path = (
        "schemas/policy.v1.schema.json"
        if policy_schema_version == "policy.v1"
        else "schemas/policy.v0.schema.json"
    )
    reason_codes_path = (
        "schemas/reason_codes.v1.json"
        if policy_schema_version == "policy.v1"
        else "schemas/reason_codes.v0.json"
    )
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

    raw_determinism = record.get("determinism")
    determinism: dict[str, Any]
    if isinstance(raw_determinism, dict):
        determinism = raw_determinism
    else:
        determinism = {}

    expected_inputs_digest = determinism.get("inputs_digest")

    # Compute candidate digests:
    # - v1-native digest (for records produced by the v1 engine)
    # - v0 digest (for v0 records, and for v0→v1 converted packs where digests weren't recomputed)
    computed_v1: str | None = None
    if request_schema_version == "decision_request.v1":
        normalized_v1 = normalize_request_v1(request)
        computed_v1 = compute_inputs_digest_v1(request, normalized=normalized_v1)

    digest_request_v0 = _decision_request_v0_equivalent(request)
    normalized_v0 = normalize_request(digest_request_v0)
    computed_v0 = compute_inputs_digest(digest_request_v0, normalized=normalized_v0)

    matched_inputs_digest: str
    if record_schema_version == "decision_record.v0":
        matched_inputs_digest = computed_v0
    elif record_schema_version == "decision_record.v1":
        if computed_v1 is not None and expected_inputs_digest == computed_v1:
            matched_inputs_digest = computed_v1
        else:
            matched_inputs_digest = computed_v0
    else:
        # Unknown version: fall back to the legacy digest algorithm for safety.
        matched_inputs_digest = computed_v0
    if expected_inputs_digest != matched_inputs_digest:
        computed_parts = []
        if computed_v1 is not None:
            computed_parts.append(f"v1={computed_v1}")
        computed_parts.append(f"v0={computed_v0}")
        die(
            "inputs_digest mismatch: "
            f"record={expected_inputs_digest} computed=({', '.join(computed_parts)})"
        )

    decision_id = record.get("decision_id")
    verdict = record.get("verdict")
    raw_reason_codes = record.get("reason_codes")
    reason_codes: list[object]
    if isinstance(raw_reason_codes, list):
        reason_codes = raw_reason_codes
    else:
        reason_codes = []

    raw_obligations = record.get("obligations")
    obligations: list[object]
    if isinstance(raw_obligations, list):
        obligations = raw_obligations
    else:
        obligations = []

    raw_context = request.get("context")
    context: dict[str, Any]
    if isinstance(raw_context, dict):
        context = raw_context
    else:
        context = {}

    if markdown:
        typer.echo(
            render_ticket_summary_markdown(
                decision_id=str(decision_id) if decision_id is not None else None,
                created_at=str(record.get("created_at")) if record.get("created_at") else None,
                verdict=str(verdict) if verdict is not None else None,
                reason_codes=[str(x) for x in reason_codes],
                policy_hash=policy_hash,
                context_digest=str(context.get("digest")) if context.get("digest") else None,
                inputs_digest=matched_inputs_digest,
                matched_rules=[
                    r for r in (record.get("matched_rules") or []) if isinstance(r, dict)
                ]
                if isinstance(record.get("matched_rules"), list)
                else [],
                obligations=[o for o in obligations if isinstance(o, dict)],
            ).rstrip("\n")
        )
    else:
        typer.echo("ok")
        typer.echo(f"decision_id: {decision_id}")
        typer.echo(f"verdict: {verdict}")
        typer.echo(f"policy_hash: {policy_hash}")
        typer.echo(f"context_digest: {context.get('digest')}")
        typer.echo(f"inputs_digest: {matched_inputs_digest}")
        if obligations:
            typer.echo(f"obligations: {len(obligations)}")
