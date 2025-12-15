from __future__ import annotations

import json
import zipfile
from pathlib import Path

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
            _zip_write_text(
                zf,
                "README.txt",
                "\n".join(
                    [
                        "Lumyn decision pack (v0)",
                        "",
                        "Files:",
                        "- decision_record.json (schema-valid DecisionRecord v0)",
                        "- policy.yml (policy snapshot by policy_hash, if available)",
                        "- request.json (original DecisionRequest)",
                        "",
                        "Replay (library):",
                        "- Validate decision_record.json against "
                        "schemas/decision_record.v0.schema.json",
                        "- Compare digests: policy_hash, context.digest, determinism.inputs_digest",
                        "",
                    ]
                ),
            )
        typer.echo(str(out))
        return

    write_json_to_path_or_stdout(record, path=out, pretty=pretty)
