from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_schemas_are_valid() -> None:
    for schema_path in sorted(Path("schemas").glob("*.schema.json")):
        schema = _load_json(schema_path)
        Draft202012Validator.check_schema(schema)


def test_examples_validate_against_schemas() -> None:
    request_schema = _load_json(Path("schemas/decision_request.v0.schema.json"))
    record_schema = _load_json(Path("schemas/decision_record.v0.schema.json"))
    policy_schema = _load_json(Path("schemas/policy.v0.schema.json"))

    request = _load_json(Path("examples/decision_request_refund.json"))
    Draft202012Validator(request_schema).validate(request)

    record = _load_json(Path("examples/decision_record_example.json"))
    Draft202012Validator(record_schema).validate(record)

    policy = _load_yaml(Path("examples/policy_support.v0.yml"))
    Draft202012Validator(policy_schema).validate(policy)
