"""Unit tests for pmo_service."""

from pathlib import Path

import pytest

from config import load_settings
from pmo_service import (
    _parse_risk_json,
    pmo_letter,
    prepare_chat_messages,
    sanitize_model_output,
)

ROOT = Path(__file__).resolve().parents[2]
PROMPTS = ROOT / "config" / "prompts"


def test_sanitize_think():
    raw = "<|think|>secret\nHello"
    assert "secret" not in sanitize_model_output(raw)
    assert "Hello" in sanitize_model_output(raw)


def test_sanitize_error_no_docs():
    assert "یافت نشد" in sanitize_model_output("ERROR_NO_DOCS")


def test_parse_risk_json():
    raw = '{"project_risks":[{"risk_title":"x","severity":"High","evidence":"e","recommended_action":"a"}]}'
    risks = _parse_risk_json(raw)
    assert len(risks) == 1
    assert risks[0]["severity"] == "High"


@pytest.mark.asyncio
async def test_prepare_chat_rag_miss(mock_lm_post, monkeypatch):
    async def _empty_search(**kwargs):
        return []

    monkeypatch.setattr("pmo_service.search", _empty_search)
    settings = load_settings()
    prep = await prepare_chat_messages(
        body={"prompt": "سوال", "use_rag": True},
        settings=settings,
        lm_post=mock_lm_post,
        prompts_dir=PROMPTS,
    )
    assert prep["used_rag"] is False
    assert "سند مرتبط" in prep["messages"][1]["content"]


@pytest.mark.asyncio
async def test_prepare_chat_empty():
    settings = load_settings()
    prep = await prepare_chat_messages(body={}, settings=settings, lm_post=None)
    assert prep.get("error")


@pytest.mark.asyncio
async def test_letter_free_only(mock_lm_chat, mock_lm_post, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "x")
    settings = load_settings()
    result = await pmo_letter(
        body={"free_prompt": "نامه تست"},
        settings=settings,
        prompts_dir=PROMPTS,
        lm_chat=mock_lm_chat,
        lm_post=mock_lm_post,
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_letter_no_fields(mock_lm_chat, mock_lm_post):
    settings = load_settings()
    result = await pmo_letter(
        body={},
        settings=settings,
        prompts_dir=PROMPTS,
        lm_chat=mock_lm_chat,
        lm_post=mock_lm_post,
    )
    assert result["status"] == "failed"
