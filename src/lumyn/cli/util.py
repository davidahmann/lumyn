from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, TextIO, cast

import typer


def _json_dumps(obj: Any, *, pretty: bool) -> str:
    if pretty:
        return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def die(message: str, *, code: int = 1) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(code=code)


@dataclass(frozen=True, slots=True)
class WorkspacePaths:
    workspace: Path
    db_path: Path
    policy_path: Path


def resolve_workspace_paths(workspace: Path) -> WorkspacePaths:
    workspace = workspace.resolve()
    return WorkspacePaths(
        workspace=workspace,
        db_path=workspace / "lumyn.db",
        policy_path=workspace / "policy.yml",
    )


def read_json_from_path_or_stdin(path: Path) -> dict[str, Any]:
    if str(path) == "-":
        return read_json_from_stdin(typer.get_text_stream("stdin"))
    return read_json_from_file(path)


def read_json_from_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"file not found: {path}")
    except json.JSONDecodeError as e:
        die(f"invalid json in {path}: {e}")
    if not isinstance(data, dict):
        die(f"expected a JSON object in {path}")
    return cast(dict[str, Any], data)


def read_json_from_stdin(stdin: TextIO) -> dict[str, Any]:
    try:
        data = json.loads(stdin.read())
    except json.JSONDecodeError as e:
        die(f"invalid json on stdin: {e}")
    if not isinstance(data, dict):
        die("expected a JSON object on stdin")
    return cast(dict[str, Any], data)


def write_json_to_path_or_stdout(obj: Any, *, path: Path, pretty: bool) -> None:
    payload = _json_dumps(obj, pretty=pretty)
    if str(path) == "-":
        typer.echo(payload, nl=False)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
