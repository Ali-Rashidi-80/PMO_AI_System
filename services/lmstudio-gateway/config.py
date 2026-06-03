"""Configuration loader for LM Studio Gateway."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    lmstudio_upstream: str
    gateway_port: int
    gateway_host: str
    max_concurrent: int
    llm_timeout_seconds: float
    n8n_internal_url: str
    webhook_secret: str
    qdrant_url: str
    llm_model_id: str
    embed_model_id: str
    pmo_docs_path: str
    prompts_path: str
    qdrant_collection: str
    max_upload_mb: int
    max_files_per_upload: int
    upload_auto_ingest: bool
    rag_reset: bool
    rag_min_score: float
    chunk_size: int
    chunk_overlap: int
    strict_clean: bool
    embed_batch_size: int


def load_settings() -> Settings:
    return Settings(
        lmstudio_upstream=os.getenv(
            "LMSTUDIO_UPSTREAM", "http://host.docker.internal:1234"
        ).rstrip("/"),
        gateway_port=int(os.getenv("GATEWAY_PORT", "8081")),
        gateway_host=os.getenv("GATEWAY_HOST", "0.0.0.0"),
        max_concurrent=int(os.getenv("MAX_CONCURRENT", "2")),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "900")),
        n8n_internal_url=os.getenv("N8N_INTERNAL_URL", "http://pmo-n8n:5678").rstrip(
            "/"
        ),
        webhook_secret=os.getenv("WEBHOOK_SECRET", "change-me-pmo-secret-2026"),
        qdrant_url=os.getenv("QDRANT_URL", "http://pmo-qdrant:6333").rstrip("/"),
        llm_model_id=os.getenv("LLM_MODEL_ID", "gemma-4-e4b-it-ud"),
        embed_model_id=os.getenv("EMBED_MODEL_ID", "nomic-embed-text-v2"),
        pmo_docs_path=os.getenv("PMO_DOCS_PATH", "/data/pmo_docs"),
        prompts_path=os.getenv("PROMPTS_PATH", "/config/prompts"),
        qdrant_collection=os.getenv("QDRANT_COLLECTION", "pmo_knowledge_base"),
        max_upload_mb=int(os.getenv("PMO_MAX_UPLOAD_MB", "30")),
        max_files_per_upload=int(os.getenv("PMO_MAX_FILES_PER_UPLOAD", "10")),
        upload_auto_ingest=_env_bool("PMO_UPLOAD_AUTO_INGEST", True),
        rag_reset=_env_bool("PMO_RAG_RESET", False),
        rag_min_score=float(os.getenv("PMO_RAG_MIN_SCORE", "0.35")),
        chunk_size=int(os.getenv("PMO_CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.getenv("PMO_CHUNK_OVERLAP", "200")),
        strict_clean=_env_bool("PMO_STRICT_CLEAN", False),
        embed_batch_size=int(os.getenv("PMO_EMBED_BATCH_SIZE", "20")),
    )
