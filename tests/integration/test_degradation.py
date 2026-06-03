"""Graceful degradation when upstream services fail."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def degraded_client(monkeypatch, tmp_path):
    monkeypatch.setenv("PMO_DOCS_PATH", str(tmp_path))
    monkeypatch.setenv("WEBHOOK_SECRET", "change-me-pmo-secret-2026")
    monkeypatch.setenv("PMO_UPLOAD_AUTO_INGEST", "false")
    import importlib
    import main as gw_main

    importlib.reload(gw_main)

    mock_lm = AsyncMock()
    mock_lm.health = AsyncMock(
        return_value={"status": "degraded", "lmstudio": "down", "models": []}
    )
    mock_lm.chat_completions = AsyncMock(
        side_effect=RuntimeError("LM Studio unavailable")
    )
    mock_lm.embeddings = AsyncMock(side_effect=RuntimeError("LM Studio unavailable"))
    mock_lm.close = AsyncMock()
    gw_main.lm = mock_lm

    transport = ASGITransport(app=gw_main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_status_when_lm_down(degraded_client):
    r = await degraded_client.get("/api/pmo/status")
    assert r.status_code == 200
    data = r.json()
    assert data["ready"] is False
    assert data["dashboard"]["lmstudio"] == "down"


@pytest.mark.asyncio
async def test_health_reports_qdrant_n8n(degraded_client):
    r = await degraded_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "qdrant" in body
    assert "n8n" in body


@pytest.mark.asyncio
async def test_upload_saves_without_auto_ingest(degraded_client, tmp_path):
    headers = {"X-PMO-Token": "change-me-pmo-secret-2026"}
    content = ("متن کافی برای ذخیره بدون ingest. " * 4).encode("utf-8")
    r = await degraded_client.post(
        "/api/pmo/documents/upload",
        headers=headers,
        files=[("files", ("saved_only.txt", content, "text/plain"))],
    )
    assert r.status_code == 200
    assert r.json()["saved"] == 1
    assert (tmp_path / "saved_only.txt").is_file()
