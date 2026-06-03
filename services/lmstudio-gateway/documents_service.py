"""Document upload, list, delete for PMO docs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from document_loader import extract_text, is_rejected, is_supported
from manifest import list_files, load_manifest, remove_file_entry, set_last_ingest, upsert_file_entry
from rag import delete_by_source_file, ingest_single_file

logger = logging.getLogger("documents")


def safe_filename(name: str) -> str:
    return Path(name.replace("\\", "/")).name


async def list_documents(docs_root: Path) -> Dict[str, Any]:
    manifest = load_manifest(docs_root)
    disk_files = []
    if docs_root.is_dir():
        for path in sorted(docs_root.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith(".") or path.name == ".pmo_index.json":
                continue
            rel = path.relative_to(docs_root).as_posix()
            disk_files.append(rel)
    manifest_names = {f.get("name") for f in manifest.get("files") or []}
    for name in disk_files:
        if name not in manifest_names:
            p = docs_root / name
            upsert_file_entry(
                docs_root,
                name=name,
                fmt=p.suffix.lstrip(".").lower(),
                size=p.stat().st_size,
                file_hash="",
                chunks=0,
                status="saved",
            )
    return {
        "status": "success",
        "files": list_files(docs_root),
        "last_ingest_at": load_manifest(docs_root).get("last_ingest_at"),
        "supported_formats": [".txt", ".docx", ".pdf", ".md", ".csv", ".json", ".log", ".text"],
    }


async def delete_document(
    *,
    docs_root: Path,
    name: str,
    settings,
) -> Dict[str, Any]:
    safe = safe_filename(name)
    target = docs_root / safe
    if not target.is_file():
        return {"status": "failed", "message": "فایل یافت نشد"}
    target.unlink(missing_ok=True)
    remove_file_entry(docs_root, safe)
    await delete_by_source_file(settings.qdrant_url, settings.qdrant_collection, safe)
    return {"status": "success", "message": f"حذف شد: {safe}"}


async def upload_documents(
    *,
    files: List[tuple],
    docs_root: Path,
    settings,
    lm_post: Callable,
) -> Dict[str, Any]:
    """files: list of (filename, bytes)."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(files) > settings.max_files_per_upload:
        return {
            "status": "failed",
            "message": f"حداکثر {settings.max_files_per_upload} فایل در هر بار",
        }

    docs_root.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    saved = skipped = 0
    total_chunks = 0

    for filename, content in files:
        safe = safe_filename(filename)
        path = docs_root / safe
        entry: Dict[str, Any] = {"name": safe}

        if is_rejected(path):
            entry.update({"status": "rejected", "reason": "فرمت پشتیبانی نمی‌شود"})
            skipped += 1
            results.append(entry)
            continue

        if not is_supported(path):
            entry.update({"status": "rejected", "reason": "فرمت پشتیبانی نمی‌شود"})
            skipped += 1
            results.append(entry)
            continue

        if len(content) > max_bytes:
            entry.update({"status": "rejected", "reason": f"حجم بیش از {settings.max_upload_mb}MB"})
            skipped += 1
            results.append(entry)
            continue

        path.write_bytes(content)
        saved += 1
        fmt = path.suffix.lstrip(".").lower()

        if settings.upload_auto_ingest:
            ing = await ingest_single_file(
                path=path,
                docs_root=docs_root,
                qdrant_url=settings.qdrant_url,
                collection=settings.qdrant_collection,
                embed_model=settings.embed_model_id,
                lm_post=lm_post,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                strict_clean=settings.strict_clean,
                embed_batch_size=settings.embed_batch_size,
            )
            status = ing.get("status", "saved")
            chunks = ing.get("chunks", 0)
            total_chunks += chunks
            upsert_file_entry(
                docs_root,
                name=safe,
                fmt=fmt,
                size=len(content),
                file_hash=ing.get("hash", ""),
                chunks=chunks,
                status=status if status == "indexed" else "pending_ingest",
                reason=ing.get("reason"),
            )
            entry.update({"status": status, "chunks": chunks, "reason": ing.get("reason")})
        else:
            text, _, err = extract_text(path, strict_clean=settings.strict_clean)
            upsert_file_entry(
                docs_root,
                name=safe,
                fmt=fmt,
                size=len(content),
                file_hash="",
                chunks=0,
                status="saved" if not err else "skipped",
                reason=err,
            )
            entry.update({"status": "saved", "chunks": 0})

        results.append(entry)
        logger.info(
            "upload file=%s status=%s chunks=%s reason=%s",
            safe,
            entry.get("status"),
            entry.get("chunks", 0),
            entry.get("reason"),
        )

    if total_chunks:
        set_last_ingest(docs_root)

    logger.info(
        "upload batch saved=%s skipped=%s ingested_chunks=%s",
        saved,
        skipped,
        total_chunks,
    )
    return {
        "status": "success",
        "saved": saved,
        "skipped": skipped,
        "ingested_chunks": total_chunks,
        "files": results,
    }
