"""Manifest helpers."""

from pathlib import Path

from manifest import load_manifest, summarize_documents, sync_manifest_after_ingest


def test_sync_manifest_after_ingest(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.txt").write_text("hello world " * 20, encoding="utf-8")
    sync_manifest_after_ingest(
        docs,
        [
            {
                "source": "a.txt",
                "path": "a.txt",
                "format": "txt",
                "file_hash": "abc",
                "chunk_idx": 0,
            },
            {
                "source": "a.txt",
                "path": "a.txt",
                "format": "txt",
                "file_hash": "abc",
                "chunk_idx": 1,
            },
        ],
    )
    data = load_manifest(docs)
    assert len(data["files"]) == 1
    assert data["files"][0]["status"] == "indexed"
    assert data["files"][0]["chunks"] == 2
    summary = summarize_documents(data["files"])
    assert summary["indexed"] == 1
    assert summary["rag_ready"] is True
