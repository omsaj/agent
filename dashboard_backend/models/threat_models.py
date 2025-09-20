from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Threat(Base):
    __tablename__ = "threats"
    __table_args__ = (
        UniqueConstraint("cve_id", name="uq_threats_cve_id"),
        Index("ix_threats_published", "published_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cve_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cvss_score: Mapped[float | None] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    modified_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    affected_products: Mapped[dict | None] = mapped_column(JSON)
    attack_vector: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str | None] = mapped_column(String(64))

    analysis: Mapped["ThreatAnalysis | None"] = relationship(
        "ThreatAnalysis", back_populates="threat", cascade="all, delete-orphan"
    )
    categories: Mapped[list["ThreatCategory"]] = relationship(
        "ThreatCategory",
        back_populates="threat",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ThreatAnalysis(Base):
    __tablename__ = "threat_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    threat_id: Mapped[int] = mapped_column(ForeignKey("threats.id", ondelete="CASCADE"))
    summary: Mapped[str | None] = mapped_column(Text)
    business_impact: Mapped[str | None] = mapped_column(Text)
    mitigation_advice: Mapped[str | None] = mapped_column(Text)
    risk_score: Mapped[float | None] = mapped_column(Float)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    threat: Mapped[Threat] = relationship("Threat", back_populates="analysis")


class ThreatCategory(Base):
    __tablename__ = "threat_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    threat_id: Mapped[int] = mapped_column(ForeignKey("threats.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float | None] = mapped_column(Float)

    threat: Mapped[Threat] = relationship("Threat", back_populates="categories")


class DashboardMetric(Base):
    __tablename__ = "dashboard_metrics"
    __table_args__ = (UniqueConstraint("metric_name", name="uq_metric_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
