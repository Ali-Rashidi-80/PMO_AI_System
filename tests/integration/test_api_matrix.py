"""API matrix tests with mocked LM."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
GATEWAY = ROOT / "services" / "lmstudio-gateway"


@pytest.fixture
def auth_headers():
    return {"X-PMO-Token": "change-me-pmo-secret-2026"}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setenv("PMO_DOCS_PATH", str(tmp_path))
    monkeypatch.setenv("WEBHOOK_SECRET", "change-me-pmo-secret-2026")
    monkeypatch.setenv("PMO_UPLOAD_AUTO_INGEST", "false")
    import importlib
    import main as gw_main
    import lm_client

    importlib.reload(gw_main)

    mock_lm = AsyncMock()
    mock_lm.health = AsyncMock(
        return_value={"status": "up", "lmstudio": "up", "models": []}
    )
    mock_lm.chat_completions = AsyncMock(
        return_value={
            "choices": [{"message": {"content": "پاسخ تست"}}],
        }
    )
    mock_lm.embeddings = AsyncMock(
        return_value={"data": [{"embedding": [0.0] * 768}]}
    )
    mock_lm.close = AsyncMock()
    gw_main.lm = mock_lm

    transport = ASGITransport(app=gw_main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_status_public(client):
    r = await client.get("/api/pmo/status")
    assert r.status_code == 200
    body = r.json()
    assert "documents_count" in body
    assert "documents_summary" in body
    assert "checked_at" in body
    assert "services" in body


@pytest.mark.asyncio
async def test_chat_empty_returns_failed(client, auth_headers):
    r = await client.post("/api/pmo/chat", json={}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_chat_stream_empty_400(client, auth_headers):
    r = await client.post("/api/pmo/chat/stream", json={}, headers=auth_headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_invalid_token(client):
    r = await client.post(
        "/api/pmo/chat",
        json={"prompt": "hi"},
        headers={"X-PMO-Token": "bad"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_letter_free_only(client, auth_headers):
    r = await client.post(
        "/api/pmo/letter",
        json={"free_prompt": "نامه"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"


@pytest.mark.asyncio
async def test_letter_docx_empty(client, auth_headers):
    r = await client.post(
        "/api/pmo/letter/docx",
        json={"letter": ""},
        headers=auth_headers,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_risk_context_only(client, auth_headers):
    r = await client.post(
        "/api/pmo/risk/run",
        json={"context": "ریسک تأخیر در تحویل"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    assert "project_risks" in r.json() or "htmlReport" in r.json()


@pytest.mark.asyncio
async def test_risk_empty_failed(client, auth_headers):
    r = await client.post("/api/pmo/risk/run", json={}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_ingest_empty_dir(client, auth_headers):
    r = await client.post("/api/pmo/ingest", json={}, headers=auth_headers)
    assert r.status_code == 200
    assert "status" in r.json()


@pytest.mark.asyncio
async def test_documents_list_auth(client, auth_headers):
    r = await client.get("/api/pmo/documents/list", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "success"
