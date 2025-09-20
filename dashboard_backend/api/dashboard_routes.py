from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.settings import get_settings
from ..models.response_models import (
    MetricsResponse,
    SummaryResponse,
    ThreatDetailResponse,
    ThreatListResponse,
    ThreatModel,
    TrendPoint,
    TrendResponse,
)
from ..models.threat_models import DashboardMetric, Threat, ThreatAnalysis
from ..services.risk_engine import risk_engine
from ..utils.database import get_session

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

settings = get_settings()


@dataclass
class CacheEntry:
    payload: Any
    expires_at: datetime


_cache: Dict[str, CacheEntry] = {}


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if not entry:
        return None
    if datetime.now(timezone.utc) > entry.expires_at:
        _cache.pop(key, None)
        return None
    return entry.payload


def _cache_set(key: str, payload: Any, ttl_seconds: int | None = None) -> None:
    ttl = ttl_seconds or settings.cache_ttl_seconds
    _cache[key] = CacheEntry(
        payload=payload, expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl)
    )


def _serialize_threat(threat: Threat) -> ThreatModel:
    analysis = None
    if threat.analysis:
        analysis = {
            "summary": threat.analysis.summary,
            "business_impact": threat.analysis.business_impact,
            "mitigation_advice": threat.analysis.mitigation_advice,
            "risk_score": threat.analysis.risk_score,
            "analyzed_at": threat.analysis.analyzed_at,
        }
    categories = [category.category for category in threat.categories]
    return ThreatModel(
        cve_id=threat.cve_id,
        title=threat.title,
        description=threat.description,
        severity=threat.severity,
        cvss_score=threat.cvss_score,
        published_date=threat.published_date,
        modified_date=threat.modified_date,
        attack_vector=threat.attack_vector,
        affected_products=threat.affected_products,
        analysis=analysis,
        categories=categories,
    )


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(session: AsyncSession = Depends(get_session)) -> SummaryResponse:
    cache_key = "summary"
    cached = _cache_get(cache_key)
    if cached:
        return SummaryResponse(**cached)

    counts_stmt = select(
        func.count().label("total"),
        func.sum(case((Threat.severity == "CRITICAL", 1), else_=0)).label("critical"),
        func.sum(case((Threat.severity == "HIGH", 1), else_=0)).label("high"),
        func.sum(case((Threat.severity == "MEDIUM", 1), else_=0)).label("medium"),
    )
    result = await session.execute(counts_stmt)
    total, critical, high, medium = result.one()

    analysis_count_stmt = select(func.count(ThreatAnalysis.id)).select_from(ThreatAnalysis)
    total_analyzed = (await session.execute(analysis_count_stmt)).scalar_one()

    recent_stmt = (
        select(Threat)
        .options(selectinload(Threat.analysis))
        .order_by(desc(Threat.modified_date))
        .limit(50)
    )
    recent_threats = (await session.execute(recent_stmt)).scalars().all()
    trending = risk_engine.identify_trending(recent_threats)
    last_update = None
    if recent_threats:
        last_update = max(
            [t.modified_date for t in recent_threats if t.modified_date]
            + [t.published_date for t in recent_threats if t.published_date]
            or [None]
        )

    response = SummaryResponse(
        critical=critical or 0,
        high=high or 0,
        medium=medium or 0,
        trending=len(trending),
        total_analyzed=total_analyzed or 0,
        last_update=last_update,
    )
    _cache_set(cache_key, response.model_dump())
    return response


@router.get("/threats", response_model=ThreatListResponse)
async def list_threats(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
    severity: Optional[str] = Query(
        None,
        pattern="^(critical|high|medium|low)$",
        description="Filter by severity level",
    ),
    days: Optional[int] = Query(None, ge=1, le=90),
) -> ThreatListResponse:
    query = select(Threat).options(
        selectinload(Threat.analysis), selectinload(Threat.categories)
    ).order_by(desc(Threat.published_date))
    count_stmt = select(func.count()).select_from(Threat)
    if severity:
        severity_upper = severity.upper()
        query = query.where(Threat.severity == severity_upper)
        count_stmt = count_stmt.where(Threat.severity == severity_upper)
    if days:
        start = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where(Threat.published_date >= start)
        count_stmt = count_stmt.where(Threat.published_date >= start)
    query = query.limit(limit)
    threats = (await session.execute(query)).scalars().unique().all()
    total = (await session.execute(count_stmt)).scalar_one()
    return ThreatListResponse(
        items=[_serialize_threat(threat) for threat in threats],
        total=total,
    )


@router.get("/threat/{cve_id}", response_model=ThreatDetailResponse)
async def get_threat_detail(
    cve_id: str, session: AsyncSession = Depends(get_session)
) -> ThreatDetailResponse:
    stmt = (
        select(Threat)
        .where(Threat.cve_id == cve_id)
        .options(selectinload(Threat.analysis), selectinload(Threat.categories))
    )
    result = await session.execute(stmt)
    threat = result.scalar_one_or_none()
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")
    return ThreatDetailResponse(threat=_serialize_threat(threat))


@router.get("/trends", response_model=TrendResponse)
async def get_trends(
    period: str = Query("30d", pattern=r"^\d+[dDwWmM]$"),
    session: AsyncSession = Depends(get_session),
) -> TrendResponse:
    cache_key = f"trends:{period}"
    cached = _cache_get(cache_key)
    if cached:
        return TrendResponse(**cached)

    amount = int(period[:-1])
    unit = period[-1].lower()
    if unit == "d":
        delta = timedelta(days=amount)
    elif unit == "w":
        delta = timedelta(weeks=amount)
    else:
        delta = timedelta(days=30 * amount)
    start = datetime.now(timezone.utc) - delta

    stmt = (
        select(func.date(Threat.published_date).label("day"), func.count())
        .where(Threat.published_date >= start)
        .group_by("day")
        .order_by("day")
    )
    rows = await session.execute(stmt)
    points = []
    for day, count in rows:
        if isinstance(day, datetime):
            parsed = day
        elif isinstance(day, date):
            parsed = datetime.combine(day, datetime.min.time())
        else:
            parsed = datetime.fromisoformat(str(day))
        points.append(TrendPoint(date=parsed, count=count))
    response = TrendResponse(points=points)
    _cache_set(cache_key, response.model_dump())
    return response


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(session: AsyncSession = Depends(get_session)) -> MetricsResponse:
    cached = _cache_get("metrics")
    if cached:
        return MetricsResponse(**cached)
    stmt = select(DashboardMetric).order_by(desc(DashboardMetric.updated_at)).limit(1)
    result = await session.execute(stmt)
    metric = result.scalar_one_or_none()
    if not metric:
        raise HTTPException(status_code=404, detail="Metrics not found")
    response = MetricsResponse(metrics=metric.metric_value, updated_at=metric.updated_at)
    _cache_set(
        "metrics", response.model_dump(), settings.metrics_cache_ttl_seconds
    )
    return response
