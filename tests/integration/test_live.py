"""Live tier — requires LM Studio on host :1234 and stack on :8080."""

from __future__ import annotations

import httpx
import pytest

from conftest import DEFAULT_TOKEN, PMO_BASE_URL, requires_lm, requires_stack

pytestmark = [pytest.mark.live, requires_stack, requires_lm]


def _headers() -> dict[str, str]:
    return {"X-PMO-Token": DEFAULT_TOKEN, "Content-Type": "application/json"}


def test_live_status_ready():
    r = httpx.get(f"{PMO_BASE_URL}/api/pmo/status", timeout=10.0)
    assert r.status_code == 200
    data = r.json()
    assert data.get("ready") is True
    assert data.get("dashboard", {}).get("lmstudio") == "up"


def test_live_chat_no_rag():
    r = httpx.post(
        f"{PMO_BASE_URL}/api/pmo/chat",
        headers=_headers(),
        json={"prompt": "یک جمله کوتاه فارسی بگو.", "use_rag": False},
        timeout=300.0,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert len(data.get("output", "")) > 5


def test_live_letter_free_prompt():
    r = httpx.post(
        f"{PMO_BASE_URL}/api/pmo/letter",
        headers=_headers(),
        json={"free_prompt": "نامه کوتاه تست acceptance"},
        timeout=300.0,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert len(data.get("letter", "")) > 10


def test_live_risk_with_context():
    r = httpx.post(
        f"{PMO_BASE_URL}/api/pmo/risk/run",
        headers=_headers(),
        json={"context": "تأخیر ۲۰ روزه در تحویل تجهیزات"},
        timeout=300.0,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    risks = data.get("project_risks") or data.get("risks") or []
    assert isinstance(risks, list)


def test_live_upload_ingest_chat_rag():
    content = ("بند ۱۲ قرارداد: تأخیر بیش از ۳۰ روز جریمه دارد. " * 8).encode("utf-8")
    up = httpx.post(
        f"{PMO_BASE_URL}/api/pmo/documents/upload",
        headers={"X-PMO-Token": DEFAULT_TOKEN},
        files=[("files", ("live_rag_test.txt", content, "text/plain"))],
        timeout=120.0,
    )
    assert up.status_code == 200
    assert up.json().get("saved", 0) >= 1

    ing = httpx.post(
        f"{PMO_BASE_URL}/api/pmo/ingest",
        headers=_headers(),
        json={},
        timeout=300.0,
    )
    assert ing.status_code == 200
    assert "status" in ing.json()

    chat = httpx.post(
        f"{PMO_BASE_URL}/api/pmo/chat",
        headers=_headers(),
        json={"prompt": "جریمه تأخیر قرارداد چیست؟", "use_rag": True},
        timeout=300.0,
    )
    assert chat.status_code == 200
    data = chat.json()
    assert data["status"] == "success"
    assert "output" in data
