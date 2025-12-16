from __future__ import annotations

import logging
from dataclasses import dataclass

from lumyn.engine.evaluator_v1 import EvaluationResultV1
from lumyn.memory.types import MemoryHit

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConsensusResult:
    verdict: str
    source: str  # "heuristic" | "memory_risk" | "memory_success"
    reason: str
    confidence: float
    memory_hits: list[MemoryHit]


def get_first_reason(result: EvaluationResultV1) -> str:
    return result.reason_codes[0] if result.reason_codes else "unknown"


class ConsensusEngine:
    """
    Arbitrates between the Heuristic Agent (Rule Engine) and the
    Semantic Agent (Memory Store).
    """

    def __init__(self) -> None:
        pass

    def arbitrate(
        self,
        heuristic_result: EvaluationResultV1,
        memory_hits: list[MemoryHit],
        risk_threshold: float = 0.9,
    ) -> ConsensusResult:
        """
        Produce a final verdict based on rules and experience.

        Logic:
        1. Heuristic Hard Veto: If rules say DENY/ABSTAIN, we usually trust them.
           (Unless we want Memory to override False Positives? For v1.3, Rules are Supreme).

        2. Memory Risk: If heuristic says ALLOW, but Memory has high similarity to FAILURE,
           we suggest ABSTAIN/ESCALATE (The "Pre-Cognition" feature).

        3. Memory Trust: If heuristic says ESCALATE, but Memory has high similarity to SUCCESS,
           we suggest ALLOW (The "Self-Healing" feature).
        """

        h_verdict = heuristic_result.verdict

        # 1. Heuristic Priority (Hard Constraints)
        if h_verdict in ("DENY", "ABSTAIN"):
            return ConsensusResult(
                verdict=h_verdict,
                source="heuristic",
                reason=f"Heuristic rule: {get_first_reason(heuristic_result)}",
                confidence=1.0,
                memory_hits=memory_hits,
            )

        # Process Memory Signals
        # Aggregate Risk and Success signals
        risk_score = 0.0
        success_score = 0.0

        top_failure = None
        top_success = None

        for hit in memory_hits:
            # Simple aggregation for v1.3: Max similarity wins
            if hit.experience.outcome == -1:  # Failure
                if hit.score > risk_score:
                    risk_score = hit.score
                    top_failure = hit
            elif hit.experience.outcome == 1:  # Success
                if hit.score > success_score:
                    success_score = hit.score
                    top_success = hit

        # 2. Risk Intervention (Pattern Matching to Failure)
        # If Heuristic allows, but we see a strong failure pattern
        if h_verdict == "ALLOW" and risk_score > risk_threshold:
            # "Pre-Cognition": Block it.
            verdict = "ABSTAIN"
            reason_code = f"High similarity ({risk_score:.2f}) to an unknown failure pattern"
            if top_failure:
                reason_code = f"High similarity ({risk_score:.2f}) to failure pattern {top_failure.experience.decision_id}"  # noqa: E501

            return ConsensusResult(
                verdict=verdict,  # Safe default
                source="memory_risk",
                reason=reason_code,
                confidence=risk_score,
                memory_hits=memory_hits,
            )

        # 3. SELF-HEALING: Check for success similarity
        # If Heuristic says ESCALATE/DENY but Memory says "This looks like a known good pattern"

        # Simple top-1 check for now
        top_success = next((h for h in memory_hits if h.experience.outcome == 1), None)
        success_score = top_success.score if top_success else 0.0

        if success_score >= 0.98:
            verdict = "ALLOW"
            reason_code = "High similarity to approved pattern"
            if top_success:
                reason_code = f"High similarity ({success_score:.2f}) to approved pattern {top_success.experience.decision_id}"  # noqa: E501

            return ConsensusResult(
                verdict=verdict,
                source="memory_success",
                reason=reason_code,
                confidence=success_score,
                memory_hits=memory_hits,
            )

        # Default: Trust Heuristic
        return ConsensusResult(
            verdict=h_verdict,
            source="heuristic",
            reason="No strong memory signal to override",
            confidence=0.5,
            memory_hits=memory_hits,
        )
