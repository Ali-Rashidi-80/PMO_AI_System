"""Document upload API tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def upload_client(monkeypatch, tmp_path):
    monkeypatch.setenv("PMO_DOCS_PATH", str(tmp_path))
    monkeypatch.setenv("WEBHOOK_SECRET", "change-me-pmo-secret-2026")
    monkeypatch.setenv("PMO_UPLOAD_AUTO_INGEST", "false")
    import importlib
    import main as gw_main

    importlib.reload(gw_main)
    from unittest.mock import AsyncMock

    mock_lm = AsyncMock()
    mock_lm.health = AsyncMock(return_value={"status": "up", "lmstudio": "up", "models": []})
    mock_lm.embeddings = AsyncMock(return_value={"data": [{"embedding": [0.0] * 768}]})
    mock_lm.close = AsyncMock()
    gw_main.lm = mock_lm

    transport = ASGITransport(app=gw_main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_upload_txt(upload_client, tmp_path):
    headers = {"X-PMO-Token": "change-me-pmo-secret-2026"}
    content = ("بند قرارداد تأخیر جریمه. " * 5).encode("utf-8")
    r = await upload_client.post(
        "/api/pmo/documents/upload",
        headers=headers,
        files=[("files", ("test.txt", content, "text/plain"))],
    )
    assert r.status_code == 200
    data = r.json()
    assert data["saved"] == 1
    assert (tmp_path / "test.txt").is_file()


@pytest.mark.asyncio
async def test_upload_reject_exe(upload_client):
    headers = {"X-PMO-Token": "change-me-pmo-secret-2026"}
    r = await upload_client.post(
        "/api/pmo/documents/upload",
        headers=headers,
        files=[("files", ("bad.exe", b"MZ", "application/octet-stream"))],
    )
    assert r.status_code == 200
    assert r.json()["files"][0]["status"] == "rejected"


@pytest.mark.asyncio
async def test_delete_missing(upload_client):
    headers = {"X-PMO-Token": "change-me-pmo-secret-2026"}
    r = await upload_client.delete("/api/pmo/documents/missing.txt", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_upload_batch_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("PMO_MAX_FILES_PER_UPLOAD", "2")
    monkeypatch.setenv("PMO_DOCS_PATH", str(tmp_path))
    monkeypatch.setenv("WEBHOOK_SECRET", "change-me-pmo-secret-2026")
    monkeypatch.setenv("PMO_UPLOAD_AUTO_INGEST", "false")
    import importlib
    import main as gw_main

    importlib.reload(gw_main)
    from unittest.mock import AsyncMock

    mock_lm = AsyncMock()
    mock_lm.health = AsyncMock(return_value={"status": "up", "lmstudio": "up", "models": []})
    mock_lm.embeddings = AsyncMock(return_value={"data": [{"embedding": [0.0] * 768}]})
    mock_lm.close = AsyncMock()
    gw_main.lm = mock_lm

    transport = ASGITransport(app=gw_main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-PMO-Token": "change-me-pmo-secret-2026"}
        files = [
            ("files", (f"f{i}.txt", ("متن کافی برای ingest تست. " * 3).encode(), "text/plain"))
            for i in range(3)
        ]
        r = await client.post("/api/pmo/documents/upload", headers=headers, files=files)
        assert r.status_code == 200
        assert r.json()["status"] == "failed"
