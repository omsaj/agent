from __future__ import annotations

from dashboard_backend.services.risk_engine import RiskFactors, risk_engine


def test_risk_engine_scoring():
    factors = RiskFactors(
        cvss_score=9.8,
        is_known_exploited=True,
        attack_vector="NETWORK",
        affected_products={"deployment": "cloud"},
    )
    score = risk_engine.compute_risk(factors)
    assert 8.0 <= score <= 10.0


def test_risk_engine_categorization():
    class DummyThreat:
        description = "This vulnerability affects web servers and HTTP interfaces"
        title = "Sample"

    category, confidence = risk_engine.categorize(DummyThreat())
    assert category == "Web"
    assert confidence >= 0.7
