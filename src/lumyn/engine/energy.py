from __future__ import annotations

from dataclasses import dataclass


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


@dataclass(frozen=True, slots=True)
class EnergySignalsV1:
    """
    Deterministic, replayable scalar risk summary ("energy") for Lumyn decisions.

    This is intentionally a cheap scoring function, not a search-based EBM.
    """

    policy_penalty: float
    failure_memory_penalty: float
    uncertainty_penalty: float
    success_memory_credit: float
    total: float


def compute_energy_v1(
    *,
    verdict: str,
    uncertainty_score: float,
    failure_similarity_score: float,
    success_similarity_score: float,
) -> EnergySignalsV1:
    """
    Compute a deterministic energy scalar in [0,1] plus a stable decomposition.

    The decomposition is meant to be replayable from the DecisionRecord alone.
    Version: energy.v1 (see `risk_signals.energy.schema_version`).
    """
    verdict_penalty_map = {
        "ALLOW": 0.0,
        "ESCALATE": 0.5,
        "DENY": 0.8,
        "ABSTAIN": 1.0,
    }
    policy_penalty = verdict_penalty_map.get(verdict, 0.6)

    failure_memory_penalty = _clamp01(float(failure_similarity_score))
    success_memory_credit = _clamp01(float(success_similarity_score))
    uncertainty_penalty = _clamp01(float(uncertainty_score))

    # Tuned to be intuitive and monotone:
    # - High failure similarity and high uncertainty push energy up.
    # - Strong success similarity can reduce energy (credit).
    raw_total = (
        policy_penalty
        + (0.7 * failure_memory_penalty)
        + (0.5 * uncertainty_penalty)
        - (0.6 * success_memory_credit)
    )
    total = _clamp01(raw_total)

    return EnergySignalsV1(
        policy_penalty=_clamp01(policy_penalty),
        failure_memory_penalty=failure_memory_penalty,
        uncertainty_penalty=uncertainty_penalty,
        success_memory_credit=success_memory_credit,
        total=total,
    )
