from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ThreatAnalysisModel(BaseModel):
    summary: Optional[str]
    business_impact: Optional[str]
    mitigation_advice: Optional[str]
    risk_score: Optional[float]
    analyzed_at: Optional[datetime]


class ThreatModel(BaseModel):
    cve_id: str
    title: str
    description: Optional[str]
    severity: str
    cvss_score: Optional[float]
    published_date: Optional[datetime]
    modified_date: Optional[datetime]
    attack_vector: Optional[str]
    affected_products: Optional[Any]
    analysis: Optional[ThreatAnalysisModel]
    categories: list[str] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    critical: int
    high: int
    medium: int
    trending: int
    total_analyzed: int
    last_update: Optional[datetime]


class ThreatListResponse(BaseModel):
    items: list[ThreatModel]
    total: int


class ThreatDetailResponse(BaseModel):
    threat: ThreatModel


class TrendPoint(BaseModel):
    date: datetime
    count: int


class TrendResponse(BaseModel):
    points: list[TrendPoint]


class MetricsResponse(BaseModel):
    metrics: dict[str, Any]
    updated_at: datetime


class ErrorResponse(BaseModel):
    detail: str
