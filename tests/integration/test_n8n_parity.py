"""n8n webhook parity — ingest/letter/risk only (not upload API)."""

from __future__ import annotations

import httpx
import pytest

from conftest import DEFAULT_TOKEN, PMO_BASE_URL, requires_stack

pytestmark = pytest.mark.integration


def _headers(token: str = DEFAULT_TOKEN) -> dict[str, str]:
    return {"X-PMO-Token": token, "Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_n8n_proxy_invalid_token():
    """Gateway /api/pmo/n8n/* rejects bad token (no n8n call needed)."""
    import importlib

    import main as gw_main

    importlib.reload(gw_main)
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=gw_main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/pmo/n8n/ingest",
            headers={"X-PMO-Token": "bad-token"},
        )
        assert r.status_code == 401


@requires_stack
def test_n8n_ingest_webhook_json():
    r = httpx.post(
        f"{PMO_BASE_URL}/webhook/pmo/ingest",
        headers=_headers(),
        json={},
        timeout=120.0,
    )
    assert r.status_code == 200
    data = r.json()
    assert "status" in data


@pytest.mark.live
@requires_stack
def test_n8n_letter_webhook_json():
    r = httpx.post(
        f"{PMO_BASE_URL}/webhook/pmo/letter",
        headers=_headers(),
        json={"free_prompt": "نامه تست parity"},
        timeout=120.0,
    )
    assert r.status_code == 200
    data = r.json()
    assert "status" in data


@pytest.mark.live
@requires_stack
def test_n8n_risk_webhook_json():
    r = httpx.post(
        f"{PMO_BASE_URL}/webhook/pmo/risk",
        headers=_headers(),
        json={"context": "ریسک تأخیر تست parity"},
        timeout=120.0,
    )
    assert r.status_code == 200
    data = r.json()
    assert "status" in data


@requires_stack
def test_gateway_vs_n8n_ingest_shape():
    """Both paths return JSON with status key (parity scope)."""
    direct = httpx.post(
        f"{PMO_BASE_URL}/api/pmo/ingest",
        headers=_headers(),
        json={},
        timeout=120.0,
    ).json()
    via_n8n = httpx.post(
        f"{PMO_BASE_URL}/webhook/pmo/ingest",
        headers=_headers(),
        json={},
        timeout=120.0,
    ).json()
    assert "status" in direct
    assert "status" in via_n8n
    assert set(direct.keys()) >= {"status"}
    assert set(via_n8n.keys()) >= {"status"}
