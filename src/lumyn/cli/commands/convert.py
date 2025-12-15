from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import typer

from lumyn.migrate.v0_v1 import decision_record_v0_to_v1, decision_request_v0_to_v1

from ..util import die, write_json_to_path_or_stdout


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"file not found: {path}")
    except json.JSONDecodeError as e:
        die(f"invalid json in {path}: {e}")
    if not isinstance(data, dict):
        die(f"expected a JSON object in {path}")
    return data


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


def _zip_write_text(zf: zipfile.ZipFile, name: str, text: str) -> None:
    zf.writestr(name, text.encode("utf-8"))


def main(
    path: Path = typer.Argument(..., help="Decision record JSON or decision pack ZIP."),
    *,
    to: str = typer.Option("v1", "--to", help="Target version: v1."),
    out: Path = typer.Option(Path("-"), "--out", help="Output path (or '-' for stdout)."),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    if to != "v1":
        die("only --to v1 is supported in this release")

    if path.suffix.lower() == ".zip":
        if str(out) == "-":
            die("pack conversion requires a file path (not stdout)")
        with zipfile.ZipFile(path) as zf:
            record = _zip_read_json(zf, "decision_record.json")
            request = _zip_read_json(zf, "request.json")
            policy_text = _zip_read_text(zf, "policy.yml")
            readme_text = _zip_read_text(zf, "README.txt")

        record_v1 = decision_record_v0_to_v1(record)
        request_v1 = decision_request_v0_to_v1(request)

        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            _zip_write_text(
                zf,
                "decision_record.json",
                json.dumps(record_v1, indent=2 if pretty else None, sort_keys=True) + "\n",
            )
            _zip_write_text(
                zf,
                "request.json",
                json.dumps(request_v1, indent=2 if pretty else None, sort_keys=True) + "\n",
            )
            _zip_write_text(zf, "policy.yml", policy_text)
            _zip_write_text(zf, "README.txt", readme_text + "\nConverted to v1.\n")
        typer.echo(str(out))
        return

    obj = _read_json(path)
    schema_version = obj.get("schema_version")
    if schema_version == "decision_record.v0":
        converted = decision_record_v0_to_v1(obj)
    elif schema_version == "decision_request.v0":
        converted = decision_request_v0_to_v1(obj)
    else:
        die("unsupported input schema_version; expected decision_record.v0 or decision_request.v0")

    write_json_to_path_or_stdout(converted, path=out, pretty=pretty)
