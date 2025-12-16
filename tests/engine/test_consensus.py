from lumyn.engine.consensus import ConsensusEngine
from lumyn.engine.evaluator_v1 import EvaluationResultV1
from lumyn.memory.types import Experience, MemoryHit


def test_heuristic_veto() -> None:
    """Verify that heuristic DENY/ABSTAIN overrides memory."""
    ce = ConsensusEngine()

    # Heuristic says DENY
    heuristic = EvaluationResultV1(
        verdict="DENY", reason_codes=["BLOCKED_USER"], matched_rules=[], queries=[], obligations=[]
    )

    # Memory says SUCCESS (sim=1.0) - irrelevant if heuristic blocks
    mem_hit = MemoryHit(experience=Experience("d1", [], 1), score=1.0)

    result = ce.arbitrate(heuristic, [mem_hit])
    assert result.verdict == "DENY"
    assert result.source == "heuristic"


def test_risk_intervention() -> None:
    """Verify memory overrides ALLOW if high risk detected."""
    ce = ConsensusEngine()

    # Heuristic says ALLOW
    heuristic = EvaluationResultV1(
        verdict="ALLOW", reason_codes=["TRUST_PATH"], matched_rules=[], queries=[], obligations=[]
    )

    # Memory says FAILURE (sim=0.95)
    mem_hit = MemoryHit(experience=Experience("d1", [], -1), score=0.95)

    result = ce.arbitrate(heuristic, [mem_hit])
    assert result.verdict == "ABSTAIN"
    assert result.source == "memory_risk"
    assert result.confidence == 0.95


def test_self_healing() -> None:
    """Verify memory overrides ESCALATE if high success detected."""
    ce = ConsensusEngine()

    # Heuristic says ESCALATE
    heuristic = EvaluationResultV1(
        verdict="ESCALATE",
        reason_codes=["HIGH_AMOUNT"],
        matched_rules=[],
        queries=[],
        obligations=[],
    )

    # Memory says SUCCESS (sim=0.99)
    mem_hit = MemoryHit(experience=Experience("d1", [], 1), score=0.99)

    result = ce.arbitrate(heuristic, [mem_hit])
    assert result.verdict == "ALLOW"
    assert result.source == "memory_success"
    assert result.confidence == 0.99


def test_default_trust() -> None:
    """Verify heuristic wins if memory signals are weak."""
    ce = ConsensusEngine()

    heuristic = EvaluationResultV1(
        verdict="ESCALATE",
        reason_codes=["HIGH_AMOUNT"],
        matched_rules=[],
        queries=[],
        obligations=[],
    )

    # Weak success signal
    mem_hit = MemoryHit(experience=Experience("d1", [], 1), score=0.5)

    result = ce.arbitrate(heuristic, [mem_hit])
    assert result.verdict == "ESCALATE"
    assert result.source == "heuristic"
