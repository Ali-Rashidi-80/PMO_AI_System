"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "services" / "lmstudio-gateway"
FIXTURES = ROOT / "tests" / "fixtures" / "documents"
PMO_BASE_URL = os.getenv("PMO_BASE_URL", "http://localhost:8080")
DEFAULT_TOKEN = os.getenv("WEBHOOK_SECRET", "change-me-pmo-secret-2026")

if str(GATEWAY) not in sys.path:
    sys.path.insert(0, str(GATEWAY))


def is_stack_up() -> bool:
    try:
        return httpx.get(f"{PMO_BASE_URL}/health", timeout=3.0).status_code == 200
    except Exception:
        return False


def is_lm_studio_up() -> bool:
    try:
        return httpx.get("http://127.0.0.1:1234/v1/models", timeout=5.0).status_code == 200
    except Exception:
        return False


requires_stack = pytest.mark.skipif(not is_stack_up(), reason="PMO stack not on :8080")
requires_lm = pytest.mark.skipif(not is_lm_studio_up(), reason="LM Studio not on :1234")


@pytest.fixture
def tmp_docs(tmp_path, monkeypatch):
    docs = tmp_path / "pmo_docs"
    docs.mkdir()
    (docs / "weekly_reports").mkdir()
    monkeypatch.setenv("PMO_DOCS_PATH", str(docs))
    monkeypatch.setenv("WEBHOOK_SECRET", "test-token-2026")
    monkeypatch.setenv("PROMPTS_PATH", str(ROOT / "config" / "prompts"))
    monkeypatch.setenv("QDRANT_URL", "http://127.0.0.1:6333")
    monkeypatch.setenv("PMO_UPLOAD_AUTO_INGEST", "false")
    return docs


@pytest.fixture
def token_headers():
    return {"X-PMO-Token": "test-token-2026"}


@pytest.fixture
def sample_txt(tmp_docs):
    p = tmp_docs / "contract_sample.txt"
    p.write_text(
        "بند ۱۲: تأخیر بیش از ۳۰ روز مشمول جریمه روزانه است.\n" * 3,
        encoding="utf-8",
    )
    return p


@pytest.fixture
def mock_embed_vector():
    return [0.1] * 768


@pytest.fixture
async def mock_lm_post(mock_embed_vector):
    async def _post(path, payload):
        if path == "/v1/embeddings":
            inputs = payload.get("input")
            if isinstance(inputs, list):
                return {
                    "data": [{"embedding": mock_embed_vector} for _ in inputs],
                }
            return {"data": [{"embedding": mock_embed_vector}]}
        raise ValueError(path)

    return _post


@pytest.fixture
async def mock_lm_chat():
    async def _chat(payload):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"project_risks":[{"risk_title":"تأخیر","severity":"High","evidence":"بند ۱۲","recommended_action":"اخطار"}]}'
                    }
                }
            ]
        }

    return _chat
