from __future__ import annotations

from lumyn.engine.similarity import top_k_matches


def test_similarity_is_deterministic_with_ties() -> None:
    query = {
        "action_type": "support.refund",
        "amount_bucket": "small",
        "tags": ["duplicate_charge"],
    }

    candidates = [
        {
            "memory_id": "mem_b",
            "label": "failure",
            "feature": {"action_type": "support.refund", "amount_bucket": "small"},
            "summary": "B",
        },
        {
            "memory_id": "mem_a",
            "label": "failure",
            "feature": {"action_type": "support.refund", "amount_bucket": "small"},
            "summary": "A",
        },
        {
            "memory_id": "mem_c",
            "label": "failure",
            "feature": {"action_type": "support.refund", "amount_bucket": "large"},
            "summary": "C",
        },
    ]

    matches = top_k_matches(query_feature=query, candidates=candidates, top_k=3)
    assert matches[0].memory_id == "mem_a"
    assert matches[1].memory_id == "mem_b"
    assert matches[2].memory_id == "mem_c"
