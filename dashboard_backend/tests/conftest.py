from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import AsyncGenerator
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dashboard_backend.api import dashboard_routes
from dashboard_backend.api.dashboard_routes import router
from dashboard_backend.models.threat_models import Base, Threat, ThreatAnalysis
from dashboard_backend.utils.database import get_session


@pytest.fixture(scope="session")
def event_loop() -> AsyncIterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture()
async def session_factory(tmp_path) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield session_maker
    finally:
        await engine.dispose()


@pytest_asyncio.fixture()
async def app(session_factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[FastAPI, None]:
    application = FastAPI()
    application.include_router(router)

    async def _get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_session] = _get_session
    dashboard_routes._cache.clear()
    yield application
    application.dependency_overrides.clear()
    dashboard_routes._cache.clear()


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture()
async def seeded_data(session_factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[None, None]:
    async with session_factory() as session:
        threat = Threat(
            cve_id="CVE-2024-0001",
            title="Test Vulnerability",
            description="A sample vulnerability for testing",
            cvss_score=8.5,
            severity="HIGH",
        )
        threat.analysis = ThreatAnalysis(
            summary="Test summary",
            business_impact="High impact",
            mitigation_advice="Apply patch",
            risk_score=7.5,
        )
        session.add(threat)
        await session.commit()
    yield
