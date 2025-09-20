from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Sequence

from openai import AsyncOpenAI

from ..config.settings import Settings
from ..models.threat_models import Threat


class LLMAnalyzer:
    """Wrapper around OpenAI to analyse CVE threats."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger("cyberscope.llm")
        self._client: AsyncOpenAI | None = None
        if settings.openai_api_key:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._token_budget = settings.daily_token_budget
        self._window_start = datetime.now(timezone.utc)
        self._tokens_used = 0
        self._lock = asyncio.Lock()

    def _reset_if_needed(self) -> None:
        if datetime.now(timezone.utc) - self._window_start > timedelta(days=1):
            self._window_start = datetime.now(timezone.utc)
            self._tokens_used = 0

    def _fallback_analysis(self, threat: Threat) -> dict:
        severity = (threat.severity or "UNKNOWN").upper()
        mitigation = "Apply vendor patches and review compensating controls." if severity in {"CRITICAL", "HIGH"} else "Monitor vendor advisories and strengthen monitoring."  # noqa: E501
        summary = threat.description[:500] if threat.description else threat.title
        return {
            "summary": summary,
            "business_impact": "Potential impact inferred from severity level.",
            "mitigation_advice": mitigation,
            "risk_score": min(10.0, (threat.cvss_score or 5) + (2 if severity == "CRITICAL" else 1)),
        }

    async def _rate_limit(self) -> None:
        await asyncio.sleep(1 / max(1, self.settings.request_rate_limit_per_sec))

    async def analyze_threat(self, threat: Threat) -> dict:
        self._reset_if_needed()
        if not self._client:
            return self._fallback_analysis(threat)

        prompt = self._build_prompt(threat)
        async with self._lock:
            self._reset_if_needed()
            if self._tokens_used >= self._token_budget:
                self.logger.warning("Token budget exceeded, using fallback analysis.")
                return self._fallback_analysis(threat)
            try:
                await self._rate_limit()
                response = await self._client.responses.create(
                    model="gpt-4o-mini",
                    input=prompt,
                    response_format={"type": "json_object"},
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("LLM analysis failed: %s", exc)
                return self._fallback_analysis(threat)

        content = response.output[0].content[0].text if response.output else "{}"
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            self.logger.error("Failed to decode LLM response: %s", content)
            return self._fallback_analysis(threat)

        usage = getattr(response, "usage", None)
        if usage and getattr(usage, "total_tokens", None):
            self._tokens_used += usage.total_tokens
        else:
            self._tokens_used += len(prompt) // 4

        return {
            "summary": payload.get("summary"),
            "business_impact": payload.get("business_impact"),
            "mitigation_advice": payload.get("mitigation_advice"),
            "risk_score": payload.get("risk_score"),
        }

    def _build_prompt(self, threat: Threat) -> str:
        template = {
            "instructions": "You are a cybersecurity analyst. Provide concise analysis in JSON.",
            "threat": {
                "cve_id": threat.cve_id,
                "title": threat.title,
                "description": threat.description,
                "cvss_score": threat.cvss_score,
                "severity": threat.severity,
                "published": threat.published_date.isoformat() if threat.published_date else None,
                "attack_vector": threat.attack_vector,
                "affected_products": threat.affected_products,
            },
            "response_schema": {
                "summary": "<string>",
                "business_impact": "<string>",
                "mitigation_advice": "<string>",
                "risk_score": "<float 0-10>",
            },
        }
        return json.dumps(template)

    async def batch_analyze(self, threats: Sequence[Threat]) -> list[dict]:
        results: list[dict] = []
        for threat in threats:
            analysis = await self.analyze_threat(threat)
            results.append(analysis)
            if self._tokens_used >= self._token_budget:
                self.logger.warning("Daily token budget reached during batch analysis.")
                break
        return results


__all__ = ["LLMAnalyzer"]
