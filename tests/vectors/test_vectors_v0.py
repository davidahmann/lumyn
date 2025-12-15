from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from lumyn.core.decide import LumynConfig, decide


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_vectors_v0_are_well_formed_schema_valid_and_match_expected_verdicts(
    tmp_path: Path,
) -> None:
    request_schema = _load_json(Path("schemas/decision_request.v0.schema.json"))
    request_validator = Draft202012Validator(request_schema)

    reason_codes_doc = _load_json(Path("schemas/reason_codes.v0.json"))
    known_reason_codes = {item["code"] for item in reason_codes_doc["codes"]}

    vector_paths = sorted(Path("vectors/v0").rglob("*.json"))
    assert vector_paths, "No vectors found under vectors/v0/"

    for idx, vector_path in enumerate(vector_paths):
        vec = _load_json(vector_path)
        assert isinstance(vec.get("name"), str) and vec["name"], f"{vector_path} missing name"
        assert "request" in vec, f"{vector_path} missing request"
        assert "expect" in vec, f"{vector_path} missing expect"

        request_validator.validate(vec["request"])

        expect = vec["expect"]
        assert expect["verdict"] in {
            "TRUST",
            "ABSTAIN",
            "ESCALATE",
            "QUERY",
        }, f"{vector_path} invalid verdict"
        reason_codes_includes = expect.get("reason_codes_includes", [])
        assert isinstance(reason_codes_includes, list), (
            f"{vector_path} reason_codes_includes not list"
        )
        for code in reason_codes_includes:
            assert code in known_reason_codes, f"{vector_path} unknown reason code: {code}"

        policy_path = vec.get("policy_path", "policies/lumyn-support.v0.yml")
        cfg = LumynConfig(
            policy_path=str(policy_path),
            store_path=tmp_path / f"vec_{idx}.db",
        )
        record = decide(vec["request"], config=cfg)
        assert record["verdict"] == expect["verdict"], f"{vector_path} verdict mismatch"
        for code in reason_codes_includes:
            assert code in record.get("reason_codes", []), (
                f"{vector_path} missing expected reason code: {code}"
            )
