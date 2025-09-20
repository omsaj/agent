from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_summary_endpoint(client, seeded_data):
    response = await client.get("/api/dashboard/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["high"] >= 1
    assert payload["total_analyzed"] >= 1


@pytest.mark.asyncio
async def test_list_threats(client, seeded_data):
    response = await client.get("/api/dashboard/threats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["cve_id"] == "CVE-2024-0001"


@pytest.mark.asyncio
async def test_threat_detail(client, seeded_data):
    response = await client.get("/api/dashboard/threat/CVE-2024-0001")
    assert response.status_code == 200
    detail = response.json()
    assert detail["threat"]["analysis"]["summary"] == "Test summary"


@pytest.mark.asyncio
async def test_trends_endpoint(client, seeded_data):
    response = await client.get("/api/dashboard/trends?period=7d")
    assert response.status_code == 200
    payload = response.json()
    assert "points" in payload


@pytest.mark.asyncio
async def test_metrics_missing_returns_404(client):
    response = await client.get("/api/dashboard/metrics")
    assert response.status_code == 404
