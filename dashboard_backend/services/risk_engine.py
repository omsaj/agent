from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

from ..models.threat_models import Threat


@dataclass
class RiskFactors:
    cvss_score: float | None
    is_known_exploited: bool
    attack_vector: str | None
    affected_products: dict | None


class RiskEngine:
    """Domain specific risk scoring for threats."""

    def __init__(self) -> None:
        self.vector_weights = {
            "NETWORK": 1.0,
            "ADJACENT_NETWORK": 0.8,
            "LOCAL": 0.6,
            "PHYSICAL": 0.3,
        }

    def compute_risk(self, factors: RiskFactors) -> float:
        base_score = (factors.cvss_score or 0) / 10
        exploit_bonus = 0.2 if factors.is_known_exploited else 0.0
        vector_weight = self.vector_weights.get(
            (factors.attack_vector or "").upper(), 0.5
        )
        product_weight = self._product_weight(factors.affected_products)
        risk = (base_score * 0.6) + (vector_weight * 0.2) + (product_weight * 0.2)
        risk += exploit_bonus
        return max(0.0, min(1.0, risk)) * 10

    def _product_weight(self, affected_products: dict | None) -> float:
        if not affected_products:
            return 0.5
        deployments = affected_products.get("deployment", "").lower()
        if any(keyword in deployments for keyword in ("cloud", "saas")):
            return 1.0
        if any(keyword in deployments for keyword in ("server", "enterprise")):
            return 0.8
        if any(keyword in deployments for keyword in ("desktop", "client")):
            return 0.6
        return 0.5

    def identify_trending(self, threats: Sequence[Threat], days: int = 7) -> list[str]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        trending = [t.cve_id for t in threats if t.published_date and t.published_date >= cutoff]
        return trending

    def categorize(self, threat: Threat) -> tuple[str, float]:
        description = (threat.description or "").lower()
        title = threat.title.lower()
        if any(keyword in description for keyword in ("web", "http", "browser")):
            return "Web", 0.75
        if any(keyword in description for keyword in ("cloud", "kubernetes", "aws", "azure")):
            return "Cloud", 0.7
        if any(keyword in description for keyword in ("mobile", "android", "ios", "iphone")):
            return "Mobile", 0.7
        if any(keyword in description for keyword in ("router", "network", "switch")):
            return "Network", 0.65
        if "firmware" in description or "iot" in description:
            return "IoT", 0.6
        if "windows" in title or "linux" in title:
            return "Endpoint", 0.55
        return "Other", 0.4

    def distribution(self, threats: Iterable[Threat]) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for threat in threats:
            category, _ = self.categorize(threat)
            counter[category] += 1
        return dict(counter)


risk_engine = RiskEngine()
