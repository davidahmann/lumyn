from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import typer

from lumyn.store.sqlite import SqliteStore

from ..util import die, resolve_workspace_paths, write_json_to_path_or_stdout
from .init import DEFAULT_POLICY_TEMPLATE, initialize_workspace

app = typer.Typer(help="Export a stored DecisionRecord as JSON (or a decision pack ZIP).")


def _json_pretty(obj: object) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _zip_write_text(zf: zipfile.ZipFile, name: str, text: str) -> None:
    zf.writestr(name, text.encode("utf-8"))


@app.callback(invoke_without_command=True)
def main(
    decision_id: str = typer.Argument(..., help="DecisionRecord decision_id to export."),
    *,
    workspace: Path = typer.Option(Path(".lumyn"), "--workspace", help="Workspace directory."),
    out: Path = typer.Option(
        Path("-"),
        "--out",
        help="Output file path (or '-' for stdout).",
    ),
    pack: bool = typer.Option(
        False,
        "--pack",
        help=(
            "Write a decision pack ZIP (decision_record.json + policy.yml + request.json + "
            "README.txt)."
        ),
    ),
    pretty: bool = typer.Option(True, "--pretty/--compact", help="Pretty-print JSON output."),
) -> None:
    paths = resolve_workspace_paths(workspace)
    if not paths.workspace.exists() or not paths.db_path.exists() or not paths.policy_path.exists():
        initialize_workspace(
            workspace=workspace, policy_template=DEFAULT_POLICY_TEMPLATE, force=False
        )

    store = SqliteStore(paths.db_path)
    store.init()
    record = store.get_decision_record(decision_id)
    if record is None:
        die(f"decision not found: {decision_id}")

    if pack or out.suffix.lower() == ".zip":
        if str(out) == "-":
            die("decision pack export requires a file path (not stdout)")
        policy_hash = (
            record.get("policy", {}).get("policy_hash")
            if isinstance(record.get("policy"), dict)
            else None
        )
        if not isinstance(policy_hash, str) or policy_hash.strip() == "":
            die("record missing policy.policy_hash")

        policy_text = store.get_policy_snapshot(policy_hash) or paths.policy_path.read_text(
            encoding="utf-8"
        )

        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            _zip_write_text(zf, "decision_record.json", _json_pretty(record))
            _zip_write_text(zf, "policy.yml", policy_text)
            request_obj = record.get("request", {})
            _zip_write_text(zf, "request.json", _json_pretty(request_obj))

            record_schema_version = record.get("schema_version")
            if not isinstance(record_schema_version, str) or record_schema_version.strip() == "":
                record_schema_version = "decision_record.v0"

            record_schema_path = (
                f"schemas/{record_schema_version}.schema.json"
                if record_schema_version in {"decision_record.v0", "decision_record.v1"}
                else "schemas/decision_record.v0.schema.json"
            )
            request_schema_version = (
                request_obj.get("schema_version")
                if isinstance(request_obj, dict)
                else "decision_request.v0"
            )
            if not isinstance(request_schema_version, str) or request_schema_version.strip() == "":
                request_schema_version = "decision_request.v0"
            request_schema_path = (
                f"schemas/{request_schema_version}.schema.json"
                if request_schema_version in {"decision_request.v0", "decision_request.v1"}
                else "schemas/decision_request.v0.schema.json"
            )

            raw_determinism = record.get("determinism")
            determinism: dict[str, Any] = (
                raw_determinism if isinstance(raw_determinism, dict) else {}
            )
            memory_snapshot_digest = None
            raw_mem = determinism.get("memory")
            if isinstance(raw_mem, dict):
                snapshot_digest = raw_mem.get("snapshot_digest")
                if isinstance(snapshot_digest, str):
                    memory_snapshot_digest = snapshot_digest

            raw_context_ref = record.get("context_ref")
            context_ref: dict[str, Any] | None = (
                raw_context_ref if isinstance(raw_context_ref, dict) else None
            )
            context_record_hash = (
                context_ref.get("record_hash")
                if isinstance(context_ref, dict) and isinstance(context_ref.get("record_hash"), str)
                else None
            )
            context_id = (
                context_ref.get("context_id")
                if isinstance(context_ref, dict) and isinstance(context_ref.get("context_id"), str)
                else None
            )

            _zip_write_text(
                zf,
                "README.txt",
                "\n".join(
                    [
                        f"Lumyn decision pack ({record_schema_version})",
                        "",
                        "Files:",
                        f"- decision_record.json (schema-valid {record_schema_version})",
                        "- policy.yml (policy snapshot by policy_hash, if available)",
                        f"- request.json (schema-valid {request_schema_version})",
                        "",
                        "Replay (library):",
                        f"- Validate decision_record.json against {record_schema_path}",
                        f"- Validate request.json against {request_schema_path}",
                        "- Compare digests: policy_hash, context.digest, determinism.inputs_digest",
                        "- If present, verify: determinism.memory.snapshot_digest",
                        "- If present, carry upstream: context_id + context_record_hash",
                        f"  - context_id: {context_id or '(absent)'}",
                        f"  - context_record_hash: {context_record_hash or '(absent)'}",
                        f"  - memory_snapshot_digest: {memory_snapshot_digest or '(absent)'}",
                        "",
                    ]
                ),
            )
        typer.echo(str(out))
        return

    write_json_to_path_or_stdout(record, path=out, pretty=pretty)
