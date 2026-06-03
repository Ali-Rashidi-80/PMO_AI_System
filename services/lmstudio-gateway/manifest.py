"""Sidecar manifest for PMO document index (.pmo_index.json)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


MANIFEST_NAME = ".pmo_index.json"


def manifest_path(docs_root: Path) -> Path:
    return docs_root / MANIFEST_NAME


def load_manifest(docs_root: Path) -> Dict[str, Any]:
    path = manifest_path(docs_root)
    if not path.is_file():
        return {"files": [], "last_ingest_at": None}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"files": [], "last_ingest_at": None}


def save_manifest(docs_root: Path, data: Dict[str, Any]) -> None:
    docs_root.mkdir(parents=True, exist_ok=True)
    manifest_path(docs_root).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def upsert_file_entry(
    docs_root: Path,
    *,
    name: str,
    fmt: str,
    size: int,
    file_hash: str,
    chunks: int = 0,
    status: str = "saved",
    reason: Optional[str] = None,
) -> None:
    data = load_manifest(docs_root)
    files: List[Dict[str, Any]] = data.get("files") or []
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "name": name,
        "format": fmt,
        "size": size,
        "hash": file_hash,
        "chunks": chunks,
        "status": status,
        "ingested_at": now if status == "indexed" else None,
        "updated_at": now,
    }
    if reason:
        entry["reason"] = reason
    files = [f for f in files if f.get("name") != name]
    files.append(entry)
    data["files"] = sorted(files, key=lambda x: x.get("name", ""))
    save_manifest(docs_root, data)


def remove_file_entry(docs_root: Path, name: str) -> None:
    data = load_manifest(docs_root)
    files = [f for f in (data.get("files") or []) if f.get("name") != name]
    data["files"] = files
    save_manifest(docs_root, data)


def set_last_ingest(docs_root: Path) -> None:
    data = load_manifest(docs_root)
    data["last_ingest_at"] = datetime.now(timezone.utc).isoformat()
    save_manifest(docs_root, data)


def sync_manifest_after_ingest(
    docs_root: Path,
    metas: List[Dict[str, Any]],
) -> None:
    """Mark files indexed in sidecar manifest after Qdrant upsert."""
    per_file: Dict[str, Dict[str, Any]] = {}
    for meta in metas:
        src = meta.get("source") or meta.get("path")
        if not src:
            continue
        if src not in per_file:
            per_file[src] = {
                "chunks": 0,
                "hash": meta.get("file_hash", ""),
                "format": meta.get("format", "txt"),
            }
        per_file[src]["chunks"] += 1
    for src, info in per_file.items():
        path = docs_root / src
        size = path.stat().st_size if path.is_file() else 0
        upsert_file_entry(
            docs_root,
            name=src,
            fmt=info["format"],
            size=size,
            file_hash=info["hash"],
            chunks=info["chunks"],
            status="indexed",
        )


def list_files(docs_root: Path) -> List[Dict[str, Any]]:
    return load_manifest(docs_root).get("files") or []


def summarize_documents(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate manifest stats for monitoring dashboards."""
    counts: Dict[str, int] = {
        "indexed": 0,
        "pending_ingest": 0,
        "saved": 0,
        "skipped": 0,
        "rejected": 0,
    }
    total_chunks = 0
    for entry in files:
        status = entry.get("status") or "saved"
        if status not in counts:
            counts[status] = 0
        counts[status] += 1
        total_chunks += int(entry.get("chunks") or 0)
    indexed = counts.get("indexed", 0)
    return {
        "total": len(files),
        "indexed": indexed,
        "pending_ingest": counts.get("pending_ingest", 0),
        "saved": counts.get("saved", 0),
        "skipped": counts.get("skipped", 0),
        "rejected": counts.get("rejected", 0),
        "total_chunks": total_chunks,
        "rag_ready": indexed > 0,
    }
