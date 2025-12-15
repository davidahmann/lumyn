from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from lumyn.core.decide import LumynConfig, decide_v1


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_vectors_v1_evaluation(tmp_path: Path) -> None:
    """
    Validates v1 evaluation logic using data-driven golden vectors.
    """
    request_schema = _load_json(Path("schemas/decision_request.v1.schema.json"))
    record_schema = _load_json(Path("schemas/decision_record.v1.schema.json"))
    request_validator = Draft202012Validator(request_schema)
    record_validator = Draft202012Validator(record_schema)

    vector_base = Path("vectors/v1/evaluation")
    if not vector_base.exists():
        return  # Skip if no vectors yet

    vector_paths = sorted(vector_base.rglob("*.json"))

    for idx, vector_path in enumerate(vector_paths):
        vec = _load_json(vector_path)
        assert "request" in vec, f"{vector_path} missing request"
        assert "expect" in vec, f"{vector_path} missing expect"

        # Validate request schema
        request_validator.validate(vec["request"])

        # Create isolate store
        store_path = tmp_path / f"vec_v1_{idx}.db"
        policy_path = Path(
            "policies/starter.v1.yml"
        )  # Default policy for vectors? Or one per vector?
        # Ideally vectors specify policy. For now we use starter.v1.yml as "Standard Policy".
        if "policy_path" in vec:
            policy_path = Path(vec["policy_path"])

        config = LumynConfig(
            policy_path=str(policy_path),
            store_path=store_path,
        )

        record = decide_v1(vec["request"], config=config)

        # Validate output schema
        record_validator.validate(record)

        expect = vec["expect"]

        # Strict checks
        assert record["verdict"] == expect["verdict"], (
            f"{vector_path}: verdict mismatch. "
            f"Got {record['verdict']}, expected {expect['verdict']}"
        )

        # Reason codes: check content + order if specified?
        # V1 spec says order matters. Let's check exact match if provided.
        if "reason_codes" in expect:
            assert record["reason_codes"] == expect["reason_codes"], (
                f"{vector_path}: reason_codes mismatch"
            )

        # Obligations: optional check
        if "obligations_titles" in expect:
            titles = [o["title"] for o in record.get("obligations", [])]
            assert set(expect["obligations_titles"]).issubset(set(titles)), (
                f"{vector_path}: missing obligations"
            )
