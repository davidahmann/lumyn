from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SimilarityMatch:
    memory_id: str
    label: str
    score: float
    summary: str | None


def _as_feature_set(feature: dict[str, Any]) -> set[str]:
    keys = set()
    for key, value in feature.items():
        if value is None:
            continue
        if isinstance(value, bool):
            keys.add(f"{key}={str(value).lower()}")
        elif isinstance(value, int | float | str):
            keys.add(f"{key}={value}")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, int | float | str):
                    keys.add(f"{key}[]={item}")
        else:
            keys.add(f"{key}=<object>")
    return keys


def weighted_jaccard(
    a: dict[str, Any], b: dict[str, Any], *, weights: dict[str, float] | None = None
) -> float:
    """
    Deterministic similarity score in [0, 1].

    We treat each feature as a string token. If `weights` are provided, they apply to features by
    *key prefix* (e.g. weight for "action_type" applies to tokens that start with
    "action_type=").
    """

    weights = weights or {}
    a_set = _as_feature_set(a)
    b_set = _as_feature_set(b)

    if not a_set and not b_set:
        return 0.0

    def token_weight(token: str) -> float:
        key = token.split("=", 1)[0].split("[]", 1)[0]
        return float(weights.get(key, 1.0))

    union = a_set | b_set
    intersection = a_set & b_set
    union_w = sum(token_weight(t) for t in union)
    if union_w <= 0:
        return 0.0
    inter_w = sum(token_weight(t) for t in intersection)
    return max(0.0, min(1.0, inter_w / union_w))


def top_k_matches(
    *,
    query_feature: dict[str, Any],
    candidates: list[dict[str, Any]],
    top_k: int = 5,
    weights: dict[str, float] | None = None,
) -> list[SimilarityMatch]:
    """
    Candidates are dicts containing at minimum:
    - memory_id: str
    - label: str
    - feature: dict
    Optional:
    - summary: str

    Tie-breaking is deterministic: sort by (score desc, memory_id asc).
    """

    scored: list[SimilarityMatch] = []
    for c in candidates:
        memory_id = c.get("memory_id")
        label = c.get("label")
        feature = c.get("feature")
        if (
            not isinstance(memory_id, str)
            or not isinstance(label, str)
            or not isinstance(feature, dict)
        ):
            continue
        score = weighted_jaccard(query_feature, feature, weights=weights)
        summary = c.get("summary") if isinstance(c.get("summary"), str) else None
        scored.append(
            SimilarityMatch(memory_id=memory_id, label=label, score=score, summary=summary)
        )

    scored.sort(key=lambda m: (-m.score, m.memory_id))
    return scored[:top_k]
