from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import httpx
from croniter import croniter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import Settings
from ..models.threat_models import DashboardMetric, Threat, ThreatAnalysis, ThreatCategory
from ..services.llm_analyzer import LLMAnalyzer
from ..services.risk_engine import RiskFactors, risk_engine

logger = logging.getLogger("cyberscope.collector")


class ThreatCollector:
    def __init__(self, settings: Settings, analyzer: LLMAnalyzer) -> None:
        self.settings = settings
        self.analyzer = analyzer
        self.session_timeout = httpx.Timeout(30.0, read=60.0)

    async def collect_nist_cves(self) -> list[dict[str, Any]]:
        """Collect recent high severity CVEs from the NVD API."""

        params = {
            "pubStartDate": (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
                "%Y-%m-%dT%H:%M:%S.000"
            ),
            "cvssV3Severity": "HIGH,CRITICAL",
            "resultsPerPage": 200,
        }
        headers = {"User-Agent": "CyberScope/1.0"}
        url = str(self.settings.nist_nvd_endpoint)
        data: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=self.session_timeout) as client:
            for attempt in range(5):
                try:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    vulnerabilities = payload.get("vulnerabilities", [])
                    for item in vulnerabilities:
                        cve = item.get("cve", {})
                        metrics = cve.get("metrics", {})
                        cvss = metrics.get("cvssMetricV31") or metrics.get("cvssMetricV30")
                        score = None
                        severity = None
                        attack_vector = None
                        if cvss:
                            metric = cvss[0].get("cvssData", {})
                            score = metric.get("baseScore")
                            severity = metric.get("baseSeverity")
                            attack_vector = metric.get("attackVector")
                        references = cve.get("references", {}).get("referenceData", [])
                        affected_products = {
                            "vendors": [n.get("vendor") for n in cve.get("affects", {}).get("vendor", {}).get("vendor_data", [])],
                            "references": references,
                        }
                        data.append(
                            {
                                "cve_id": cve.get("id"),
                                "title": cve.get("descriptions", [{}])[0].get("value", ""),
                                "description": self._extract_description(cve.get("descriptions", [])),
                                "cvss_score": score,
                                "severity": severity or "UNKNOWN",
                                "published_date": cve.get("published"),
                                "modified_date": cve.get("lastModified"),
                                "affected_products": affected_products,
                                "attack_vector": attack_vector,
                                "source": "NVD",
                            }
                        )
                    break
                except (httpx.HTTPError, json.JSONDecodeError) as exc:  # noqa: BLE001
                    logger.warning("NVD collection error: %s", exc)
                    await asyncio.sleep(2 ** attempt)
        return data

    async def collect_cisa_kev(self) -> set[str]:
        url = str(self.settings.cisa_kev_endpoint)
        async with httpx.AsyncClient(timeout=self.session_timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
                return {item.get("cveID") for item in payload.get("vulnerabilities", [])}
            except (httpx.HTTPError, json.JSONDecodeError) as exc:  # noqa: BLE001
                logger.warning("Failed to fetch CISA KEV list: %s", exc)
                return set()

    async def collect_github_advisories(self) -> list[dict[str, Any]]:
        # Placeholder for GitHub GraphQL query; requires token in headers when available.
        return []

    async def store_threats(
        self,
        session: AsyncSession,
        threats: Iterable[dict[str, Any]],
        exploited: set[str],
    ) -> list[Threat]:
        stored: list[Threat] = []
        for item in threats:
            stmt = select(Threat).where(Threat.cve_id == item["cve_id"])
            result = await session.execute(stmt)
            threat = result.scalar_one_or_none()
            if threat:
                threat.title = item.get("title", threat.title)
                threat.description = item.get("description", threat.description)
                threat.cvss_score = item.get("cvss_score", threat.cvss_score)
                threat.severity = item.get("severity", threat.severity)
                threat.published_date = self._parse_date(item.get("published_date"))
                threat.modified_date = self._parse_date(item.get("modified_date"))
                threat.affected_products = item.get("affected_products", threat.affected_products)
                threat.attack_vector = item.get("attack_vector", threat.attack_vector)
            else:
                threat = Threat(
                    cve_id=item["cve_id"],
                    title=item.get("title", ""),
                    description=item.get("description"),
                    cvss_score=item.get("cvss_score"),
                    severity=item.get("severity", "UNKNOWN"),
                    published_date=self._parse_date(item.get("published_date")),
                    modified_date=self._parse_date(item.get("modified_date")),
                    affected_products=item.get("affected_products"),
                    attack_vector=item.get("attack_vector"),
                    source=item.get("source"),
                )
                session.add(threat)
            risk = risk_engine.compute_risk(
                RiskFactors(
                    cvss_score=threat.cvss_score,
                    is_known_exploited=threat.cve_id in exploited,
                    attack_vector=threat.attack_vector,
                    affected_products=threat.affected_products,
                )
            )
            if not threat.analysis:
                analysis_payload = await self.analyzer.analyze_threat(threat)
                threat.analysis = ThreatAnalysis(
                    summary=analysis_payload.get("summary"),
                    business_impact=analysis_payload.get("business_impact"),
                    mitigation_advice=analysis_payload.get("mitigation_advice"),
                    risk_score=analysis_payload.get("risk_score", risk),
                    analyzed_at=datetime.now(timezone.utc),
                )
            else:
                threat.analysis.risk_score = threat.analysis.risk_score or risk
            category_label, confidence = risk_engine.categorize(threat)
            if not any(cat.category == category_label for cat in threat.categories):
                threat.categories.append(
                    ThreatCategory(category=category_label, confidence=confidence)
                )
            stored.append(threat)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.exception("Failed to store threats due to integrity error.")
        return stored

    async def update_metrics(self, session: AsyncSession, threats: list[Threat]) -> None:
        total = len(threats)
        trending = risk_engine.identify_trending(threats)
        metric_payload = {
            "total_collected": total,
            "trending": trending,
            "categories": risk_engine.distribution(threats),
        }
        stmt = select(DashboardMetric).where(DashboardMetric.metric_name == "threat_snapshot")
        result = await session.execute(stmt)
        metric = result.scalar_one_or_none()
        if metric:
            metric.metric_value = metric_payload
            metric.updated_at = datetime.now(timezone.utc)
        else:
            metric = DashboardMetric(metric_name="threat_snapshot", metric_value=metric_payload)
            session.add(metric)
        await session.commit()

    async def run_collection(self, session: AsyncSession) -> list[Threat]:
        logger.info("Starting threat data collection run")
        nist_data, cisa_data = await asyncio.gather(
            self.collect_nist_cves(), self.collect_cisa_kev()
        )
        github_data = await self.collect_github_advisories()
        merged = nist_data + github_data
        stored = await self.store_threats(session, merged, cisa_data)
        if stored:
            await self.update_metrics(session, stored)
        logger.info("Threat collection completed with %d records", len(stored))
        return stored

    async def schedule_collection(self, session_factory) -> None:
        cron = croniter(self.settings.collection_schedule, datetime.now(timezone.utc))
        while True:
            next_run = cron.get_next(datetime)
            delay = (next_run - datetime.now(timezone.utc)).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)
            async with session_factory() as session:
                try:
                    await self.run_collection(session)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Scheduled collection failed: %s", exc)

    def _parse_date(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            return None

    def _extract_description(self, descriptions: list[dict[str, Any]]) -> str:
        if not descriptions:
            return ""
        for item in descriptions:
            if item.get("lang") == "en":
                return item.get("value", "")
        return descriptions[0].get("value", "")


__all__ = ["ThreatCollector"]
