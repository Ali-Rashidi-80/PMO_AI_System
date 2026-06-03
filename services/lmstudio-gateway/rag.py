"""Qdrant RAG helpers — ingest and search without n8n."""

from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import httpx

from document_loader import extract_text, iter_document_paths
from manifest import sync_manifest_after_ingest

logger = logging.getLogger("rag")

EMBED_FALLBACKS = ["nomic-embed-text-v2", "text-embedding-nomic-embed-text-v1.5"]

_ingest_lock: Optional[Any] = None


def _get_lock():
    import asyncio

    global _ingest_lock  # noqa: PLW0603
    if _ingest_lock is None:
        _ingest_lock = asyncio.Lock()
    return _ingest_lock


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def chunk_text(text: str, size: int = 1000, overlap: int = 200) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


async def ensure_collection(
    client: httpx.AsyncClient,
    qdrant_url: str,
    collection: str,
    vector_size: int = 768,
    *,
    recreate: bool = False,
) -> None:
    url = f"{qdrant_url}/collections/{collection}"
    if recreate:
        await client.delete(url)
    resp = await client.get(url)
    if resp.status_code == 200:
        return
    await client.put(
        url,
        json={"vectors": {"size": vector_size, "distance": "Cosine"}},
    )
    resp.raise_for_status()


async def delete_by_source(
    client: httpx.AsyncClient,
    qdrant_url: str,
    collection: str,
    source: str,
) -> None:
    resp = await client.post(
        f"{qdrant_url}/collections/{collection}/points/delete",
        json={
            "filter": {
                "must": [{"key": "source", "match": {"value": source}}],
            }
        },
    )
    if resp.status_code not in (200, 404):
        resp.raise_for_status()


async def delete_orphan_sources(
    client: httpx.AsyncClient,
    qdrant_url: str,
    collection: str,
    valid_sources: Set[str],
) -> None:
    """Remove points whose source file no longer exists on disk."""
    scroll_resp = await client.post(
        f"{qdrant_url}/collections/{collection}/points/scroll",
        json={"limit": 500, "with_payload": True, "with_vector": False},
    )
    if scroll_resp.status_code != 200:
        return
    orphans: Set[str] = set()
    for point in scroll_resp.json().get("result", {}).get("points", []):
        src = (point.get("payload") or {}).get("source")
        if src and src not in valid_sources:
            orphans.add(src)
    for src in orphans:
        await delete_by_source(client, qdrant_url, collection, src)


async def embed_texts(
    lm_post: Callable,
    model: str,
    texts: List[str],
    *,
    batch_size: int = 20,
) -> List[List[float]]:
    models_to_try = [model] + [m for m in EMBED_FALLBACKS if m != model]
    last_error: Optional[Exception] = None
    for embed_model in models_to_try:
        vectors: List[List[float]] = []
        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                if len(batch) == 1:
                    data = await lm_post(
                        "/v1/embeddings", {"model": embed_model, "input": batch[0]}
                    )
                    vectors.append(data["data"][0]["embedding"])
                else:
                    data = await lm_post(
                        "/v1/embeddings", {"model": embed_model, "input": batch}
                    )
                    for item in data.get("data", []):
                        vectors.append(item["embedding"])
            return vectors
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            vectors = []
            continue
    if last_error:
        raise last_error
    return []


def collect_document_chunks(
    docs_path: Path,
    *,
    chunk_size: int,
    chunk_overlap: int,
    strict_clean: bool,
    known_hashes: Optional[Dict[str, str]] = None,
) -> tuple[List[str], List[str], List[Dict[str, Any]], List[str]]:
    """Returns texts, sources, meta list, skip reasons."""
    texts: List[str] = []
    sources: List[str] = []
    metas: List[Dict[str, Any]] = []
    skips: List[str] = []
    known_hashes = known_hashes or {}

    for path in iter_document_paths(docs_path):
        rel = path.relative_to(docs_path)
        source = rel.as_posix()
        try:
            fhash = file_hash(path)
        except OSError as exc:
            skips.append(f"{source}: {exc}")
            continue
        if known_hashes.get(source) == fhash:
            continue
        text, fmt, err = extract_text(path, strict_clean=strict_clean)
        if err:
            skips.append(f"{source}: {err}")
            continue
        if len(text) < 10:
            skips.append(f"{source}: متن کوتاه")
            continue
        for idx, chunk in enumerate(chunk_text(text, chunk_size, chunk_overlap)):
            texts.append(chunk)
            sources.append(source)
            metas.append(
                {
                    "source": source,
                    "path": source,
                    "format": fmt,
                    "file_hash": fhash,
                    "chunk_idx": idx,
                }
            )
    return texts, sources, metas, skips


async def upsert_chunks(
    *,
    texts: List[str],
    sources: List[str],
    metas: List[Dict[str, Any]],
    qdrant_url: str,
    collection: str,
    embed_model: str,
    lm_post: Callable,
    embed_batch_size: int = 20,
    rag_reset: bool = False,
) -> int:
    if not texts:
        return 0
    vectors = await embed_texts(
        lm_post, embed_model, texts, batch_size=embed_batch_size
    )
    dim = len(vectors[0]) if vectors else 768

    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        await ensure_collection(client, qdrant_url, collection, dim, recreate=rag_reset)
        points = []
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        for text, source, meta, vector in zip(texts, sources, metas, vectors):
            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{meta['file_hash']}:{meta['chunk_idx']}",
                )
            )
            payload = {
                "text": text,
                "source": source,
                "path": meta["path"],
                "format": meta["format"],
                "file_hash": meta["file_hash"],
                "ingested_at": now,
            }
            points.append({"id": point_id, "vector": vector, "payload": payload})
        batch_size = 32
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            resp = await client.put(
                f"{qdrant_url}/collections/{collection}/points",
                json={"points": batch},
            )
            resp.raise_for_status()
    return len(points)


async def ingest_directory(
    *,
    docs_path: Path,
    qdrant_url: str,
    collection: str,
    embed_model: str,
    lm_post: Callable,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    strict_clean: bool = False,
    embed_batch_size: int = 20,
    rag_reset: bool = False,
    rag_min_score: float = 0.0,
) -> Dict[str, Any]:
    del rag_min_score  # used in search only
    if not docs_path.is_dir():
        return {"status": "failed", "message": f"مسیر یافت نشد: {docs_path}", "count": 0}

    async with _get_lock():
        known_hashes: Dict[str, str] = {}
        texts, sources, metas, skips = collect_document_chunks(
            docs_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strict_clean=strict_clean,
            known_hashes=known_hashes if not rag_reset else {},
        )

        valid_sources = {
            p.relative_to(docs_path).as_posix()
            for p in iter_document_paths(docs_path)
        }

        if not texts and not rag_reset:
            if skips:
                return {
                    "status": "failed",
                    "message": "هیچ سند معتبری یافت نشد",
                    "count": 0,
                    "skips": skips,
                }
            return {"status": "failed", "message": "هیچ سند معتبری یافت نشد", "count": 0}

        try:
            count = await upsert_chunks(
                texts=texts,
                sources=sources,
                metas=metas,
                qdrant_url=qdrant_url,
                collection=collection,
                embed_model=embed_model,
                lm_post=lm_post,
                embed_batch_size=embed_batch_size,
                rag_reset=rag_reset,
            )
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                await delete_orphan_sources(client, qdrant_url, collection, valid_sources)
            sync_manifest_after_ingest(docs_path, metas)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("ingest failed")
            return {"status": "failed", "message": str(exc), "count": 0, "skips": skips}

        logger.info(
            "ingest event files=%s chunks=%s skips=%s",
            len(valid_sources),
            count,
            len(skips),
        )
        return {
            "status": "success",
            "message": "Ingest completed",
            "count": count,
            "chunks": count,
            "files": len(valid_sources),
            "skips": skips,
        }


async def ingest_single_file(
    *,
    path: Path,
    docs_root: Path,
    qdrant_url: str,
    collection: str,
    embed_model: str,
    lm_post: Callable,
    chunk_size: int,
    chunk_overlap: int,
    strict_clean: bool,
    embed_batch_size: int,
) -> Dict[str, Any]:
    source = path.relative_to(docs_root).as_posix()
    await delete_by_source_file(qdrant_url, collection, source)
    text, fmt, err = extract_text(path, strict_clean=strict_clean)
    if err:
        return {"status": "skipped", "reason": err, "chunks": 0, "format": fmt}
    if len(text) < 10:
        return {"status": "skipped", "reason": "متن کوتاه", "chunks": 0, "format": fmt}
    fhash = file_hash(path)
    texts, sources, metas = [], [], []
    for idx, chunk in enumerate(chunk_text(text, chunk_size, chunk_overlap)):
        texts.append(chunk)
        sources.append(source)
        metas.append(
            {
                "source": source,
                "path": source,
                "format": fmt,
                "file_hash": fhash,
                "chunk_idx": idx,
            }
        )
    try:
        count = await upsert_chunks(
            texts=texts,
            sources=sources,
            metas=metas,
            qdrant_url=qdrant_url,
            collection=collection,
            embed_model=embed_model,
            lm_post=lm_post,
            embed_batch_size=embed_batch_size,
        )
        return {"status": "indexed", "chunks": count, "format": fmt, "hash": fhash}
    except Exception as exc:  # pylint: disable=broad-except
        return {"status": "pending_ingest", "reason": str(exc), "chunks": 0, "format": fmt}


async def delete_by_source_file(qdrant_url: str, collection: str, source: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            await delete_by_source(client, qdrant_url, collection, source)
    except Exception:  # pylint: disable=broad-except
        pass


async def search(
    *,
    query: str,
    qdrant_url: str,
    collection: str,
    embed_model: str,
    lm_post: Callable,
    limit: int = 5,
    min_score: float = 0.0,
    embed_batch_size: int = 20,
) -> List[Dict[str, Any]]:
    try:
        vectors = await embed_texts(
            lm_post, embed_model, [query], batch_size=embed_batch_size
        )
    except Exception:  # pylint: disable=broad-except
        return []
    if not vectors:
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            check = await client.get(f"{qdrant_url}/collections/{collection}")
            if check.status_code != 200:
                return []
            resp = await client.post(
                f"{qdrant_url}/collections/{collection}/points/search",
                json={"vector": vectors[0], "limit": limit, "with_payload": True},
            )
            if resp.status_code != 200:
                return []
            hits = resp.json().get("result", [])
            return [
                {
                    "text": h.get("payload", {}).get("text", ""),
                    "source": h.get("payload", {}).get("source", ""),
                    "score": h.get("score"),
                }
                for h in hits
                if h.get("payload", {}).get("text")
                and (h.get("score") or 0) >= min_score
            ]
    except Exception:  # pylint: disable=broad-except
        return []


def read_text_files(directory: Path) -> str:
    from document_loader import read_documents

    return read_documents(directory)


def format_context(hits: List[Dict[str, Any]]) -> str:
    if not hits:
        return ""
    lines = ["اسناد بازیابی‌شده:"]
    for i, hit in enumerate(hits, 1):
        lines.append(f"[{i}] ({hit.get('source', '?')}): {hit.get('text', '')[:800]}")
    return "\n".join(lines)


# Backward-compat aliases for tests
_clean_text = lambda raw: __import__("document_loader").clean_text(raw)  # noqa: E731
_chunk_text = chunk_text
