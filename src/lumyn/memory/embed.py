from __future__ import annotations

from collections.abc import Sequence

from fastembed import TextEmbedding

from lumyn.engine.normalize_v1 import NormalizedRequestV1

# Model choice: BAAI/bge-small-en-v1.5 is small (133MB), fast, and good for retrieval
DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"


class ProjectionLayer:
    """
    Project normalized requests into a vector space suitable for
    similarity search (experience memory).
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model = TextEmbedding(model_name=model_name)

    def embed_request(self, normalized: NormalizedRequestV1) -> list[float]:
        """
        Embed a single NormalizedRequest into a float vector.
        """
        # We need a text representation of the request.
        # Format: "Action: <type> <intent> <amount>. Evidence: <key>=<val>"
        text = self._to_text(normalized)
        # fastembed returns a generator of vectors
        vectors = list(self.model.embed([text]))
        return list(vectors[0])

    def embed_batch(self, requests: Sequence[NormalizedRequestV1]) -> list[list[float]]:
        texts = [self._to_text(req) for req in requests]
        return [list(v) for v in self.model.embed(texts)]

    def _to_text(self, n: NormalizedRequestV1) -> str:
        """
        Convert normalized request to semantically meaningful text.
        """
        # Construction strategy:
        # "Action: refund. Amount: 100 USD. Evidence: risk_score=0.9, user_age=10."
        parts = [
            f"Action: {n.action_type}",
        ]
        # v1 normalized request does not currently capture intent separate from type
        # if identifying intent becomes critical for retrieval, we should add it to NormalizedRequestV1  # noqa: E501

        amt_str = []
        if n.amount_value is not None:
            amt_str.append(str(n.amount_value))
        if n.amount_currency:
            amt_str.append(n.amount_currency)

        if amt_str:
            parts.append(f"Amount: {' '.join(amt_str)}")

        evidence_parts = []
        # Sort keys for determinism in text construction
        for k in sorted(n.evidence.keys()):
            val = n.evidence[k]
            if val is not None:
                evidence_parts.append(f"{k}={val}")

        if evidence_parts:
            parts.append(f"Evidence: {', '.join(evidence_parts)}")

        return ". ".join(parts)
