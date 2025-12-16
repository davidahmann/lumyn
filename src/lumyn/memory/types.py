from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Verdict = Literal["ALLOW", "DENY", "ABSTAIN", "ESCALATE"]
Outcome = Literal["SUCCESS", "FAILURE"]  # Simplified for v1.3


@dataclass
class Experience:
    """
    A single unit of experience stored in memory.
    Represents a past decision and its verified outcome.
    """

    decision_id: str
    vector: list[float]  # The projected embedding

    # Metadata for outcome analysis
    outcome: int  # 1 (Success) or -1 (Failure)
    severity: int = 1  # 1..5

    # Traceability
    original_verdict: Verdict = "ESCALATE"
    timestamp: str = ""  # ISO format

    # LanceDB requires pyarrow-compatible types usually,
    # but the python client handles dataclasses well.


@dataclass
class MemoryHit:
    """
    A result from a memory query.
    """

    experience: Experience
    score: float
