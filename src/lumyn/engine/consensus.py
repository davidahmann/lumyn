from __future__ import annotations

import logging
from dataclasses import dataclass

from lumyn.engine.evaluator_v1 import EvaluationResultV1
from lumyn.memory.types import MemoryHit

logger = logging.getLogger(__name__)

REASON_FAILURE_MEMORY_SIMILAR_BLOCK = "FAILURE_MEMORY_SIMILAR_BLOCK"
REASON_SUCCESS_MEMORY_SIMILAR_ALLOW = "SUCCESS_MEMORY_SIMILAR_ALLOW"


@dataclass(frozen=True, slots=True)
class ConsensusResult:
    verdict: str
    source: str  # "heuristic" | "memory_risk" | "memory_success"
    reason: str
    confidence: float  # How confident we are in the verdict (0.0 - 1.0)
    uncertainty: float  # 1.0 - strongest memory signal; high = novel pattern
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
        # For hard denials, rules are definitive regardless of memory
        if h_verdict in ("DENY", "ABSTAIN"):
            # Even for hard rules, compute memory signal for uncertainty
            strongest_signal = 0.0
            for hit in memory_hits:
                strongest_signal = max(strongest_signal, hit.score)
            return ConsensusResult(
                verdict=h_verdict,
                source="heuristic",
                reason=f"Heuristic rule: {get_first_reason(heuristic_result)}",
                confidence=1.0,  # Rules are always confident
                uncertainty=1.0 - strongest_signal,  # Novel if no memory
                memory_hits=memory_hits,
            )

        # Process Memory Signals
        # Aggregate Risk and Success signals
        risk_score = 0.0
        success_score = 0.0

        for hit in memory_hits:
            # Simple aggregation for v1.3: Max similarity wins
            if hit.experience.outcome == -1:  # Failure
                risk_score = max(risk_score, hit.score)
            elif hit.experience.outcome == 1:  # Success
                success_score = max(success_score, hit.score)

        # 2. Risk Intervention (Pattern Matching to Failure)
        # If Heuristic allows, but we see a strong failure pattern
        if h_verdict == "ALLOW" and risk_score > risk_threshold:
            # "Pre-Cognition": Block it.
            verdict = "ABSTAIN"
            reason_code = REASON_FAILURE_MEMORY_SIMILAR_BLOCK

            return ConsensusResult(
                verdict=verdict,  # Safe default
                source="memory_risk",
                reason=reason_code,
                confidence=risk_score,
                uncertainty=1.0 - risk_score,  # Low uncertainty - we have evidence
                memory_hits=memory_hits,
            )

        # 3. SELF-HEALING: Check for success similarity
        # If Heuristic says ESCALATE/DENY but Memory says "This looks like a known good pattern"

        if success_score >= 0.98:
            verdict = "ALLOW"
            reason_code = REASON_SUCCESS_MEMORY_SIMILAR_ALLOW

            return ConsensusResult(
                verdict=verdict,
                source="memory_success",
                reason=reason_code,
                confidence=success_score,
                uncertainty=1.0 - success_score,  # Low uncertainty - we have evidence
                memory_hits=memory_hits,
            )

        # Default: Trust Heuristic
        # Uncertainty is high if no strong memory signal exists
        strongest_signal = max(risk_score, success_score)
        return ConsensusResult(
            verdict=h_verdict,
            source="heuristic",
            reason="No strong memory signal to override",
            confidence=0.5 + (strongest_signal * 0.5),  # Modest boost from weak signals
            uncertainty=1.0 - strongest_signal,  # High if novel pattern
            memory_hits=memory_hits,
        )
