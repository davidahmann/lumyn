from lumyn.engine.normalize_v1 import NormalizedRequestV1
from lumyn.memory.embed import ProjectionLayer


def test_embed_request_determinism() -> None:
    """
    Ensure the embedding is deterministic and has correct dimensions.
    """
    proj = ProjectionLayer()

    req1 = NormalizedRequestV1(
        action_type="refund",
        amount_value=100.0,
        amount_currency="USD",
        evidence={"risk_score": 0.5},
        amount_usd=100.0,
        fx_rate_to_usd_present=True,
    )

    # Run twice
    vec1 = proj.embed_request(req1)
    vec2 = proj.embed_request(req1)

    assert len(vec1) == 384  # Default dimension for BAAI/bge-small-en-v1.5
    assert vec1 == vec2


def test_embed_text_representation() -> None:
    """
    Verify the text construction logic.
    """
    proj = ProjectionLayer()
    req = NormalizedRequestV1(
        action_type="login",
        evidence={"device": "mobile", "ip_score": 0.9},
        amount_value=None,
        amount_currency=None,
        amount_usd=None,
        fx_rate_to_usd_present=False,
    )

    text = proj._to_text(req)
    # Action: login. Evidence: device=mobile, ip_score=0.9
    assert "Action: login" in text
    assert "Evidence: device=mobile, ip_score=0.9" in text
