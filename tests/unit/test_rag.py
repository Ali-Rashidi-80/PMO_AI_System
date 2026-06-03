"""Unit tests for rag helpers."""

import pytest

from rag import chunk_text, format_context, file_hash


def test_chunk_text_overlap():
    text = "a" * 2500
    chunks = chunk_text(text, size=1000, overlap=200)
    assert len(chunks) >= 2
    assert chunks[0][:100] == "a" * 100


def test_chunk_empty():
    assert chunk_text("") == []


def test_format_context_empty():
    assert format_context([]) == ""


def test_format_context_hits():
    ctx = format_context([{"source": "a.txt", "text": "hello"}])
    assert "a.txt" in ctx


def test_file_hash(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"same")
    assert file_hash(p) == file_hash(p)


@pytest.mark.asyncio
async def test_delete_by_source():
    from unittest.mock import AsyncMock, MagicMock

    from rag import delete_by_source

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    client = AsyncMock()
    client.post = AsyncMock(return_value=mock_response)

    await delete_by_source(client, "http://qdrant.test", "pmo", "a.txt")
    client.post.assert_called_once()
    assert "points/delete" in client.post.call_args[0][0]


@pytest.mark.asyncio
async def test_ingest_missing_dir(mock_lm_post, tmp_path):
    from rag import ingest_directory

    result = await ingest_directory(
        docs_path=tmp_path / "nope",
        qdrant_url="http://127.0.0.1:6333",
        collection="test",
        embed_model="nomic-embed-text-v2",
        lm_post=mock_lm_post,
    )
    assert result["status"] == "failed"
