from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_record_chain_refs_schema_accepts_valid_vectors() -> None:
    schema = _load_json(Path("schemas/record_chain_refs.v1.schema.json"))
    validator = Draft202012Validator(schema)

    context_ref = _load_json(Path("vectors/shared/refs/v1/context_ref_valid.json"))
    decision_ref = _load_json(Path("vectors/shared/refs/v1/decision_ref_valid.json"))
    receipt_ref = _load_json(Path("vectors/shared/refs/v1/receipt_ref_valid.json"))

    validator.validate(
        {"schema_version": "record_chain_refs.v1", "context_ref": context_ref},
    )
    validator.validate(
        {"schema_version": "record_chain_refs.v1", "decision_ref": decision_ref},
    )
    validator.validate(
        {"schema_version": "record_chain_refs.v1", "receipt_ref": receipt_ref},
    )


def test_record_chain_refs_schema_rejects_invalid_hash_vector() -> None:
    schema = _load_json(Path("schemas/record_chain_refs.v1.schema.json"))
    validator = Draft202012Validator(schema)

    bad = _load_json(Path("vectors/shared/refs/v1/context_ref_invalid_hash.json"))
    with pytest.raises(Exception):
        validator.validate({"schema_version": "record_chain_refs.v1", "context_ref": bad})


def test_interaction_ref_schema_accepts_voice_vector() -> None:
    schema = _load_json(Path("schemas/interaction_ref.v0.schema.json"))
    validator = Draft202012Validator(schema)
    voice = _load_json(Path("vectors/shared/interaction_ref/v0/voice_valid.json"))
    validator.validate(voice)


def test_interaction_ref_schema_rejects_bad_digest() -> None:
    schema = _load_json(Path("schemas/interaction_ref.v0.schema.json"))
    validator = Draft202012Validator(schema)
    bad = _load_json(Path("vectors/shared/interaction_ref/v0/voice_invalid_timeline_hash.json"))
    with pytest.raises(Exception):
        validator.validate(bad)
