# PMO Document Import



## Supported formats (LM Studio aligned)



| Tier | Extensions |

|------|------------|

| L1 | `.txt`, `.docx`, `.pdf` |

| L2 | `.md`, `.csv`, `.json`, `.log`, `.text` |



**Limits:** 30MB per file, 10 files per upload batch.



## Runbook



1. Open LM Studio → Load **nomic-embed-text-v2** (or v1.5 fallback)

2. Start Server on port 1234

3. Upload or click **به‌روزرسانی همه اسناد** in UI

4. For chat/letter/risk: Unload embed model → Load **gemma-4-e4b-it-ud** → Start Server



## First deploy after upgrade



Set `PMO_RAG_RESET=true` once in docker-compose, run ingest, then set back to `false`.



## Observability



| Signal | Where |

|--------|--------|

| `documents_count`, `last_ingest_at` | `GET /api/pmo/status` + Settings card |

| `embed_model`, `llm_model` | `/health` + Settings LM card |

| `rag_min_score` | `GET /api/pmo/status` (default 0.35) |

| Per-file upload | gateway log `upload file=... status=...` |

| Full ingest | gateway log `ingest event files=... chunks=...` |

| Manifest sidecar | `pmo_docs/.pmo_index.json` (not committed) |



## Graceful degradation



| Condition | Behavior |

|-----------|----------|

| LM Studio down on upload | File saved; manifest `pending_ingest` if auto-ingest enabled |

| Qdrant down | Upload OK; ingest returns failed — retry after Qdrant up |

| n8n down | Gateway `/api/pmo/*` still works; webhooks fail |

| RAG miss (score < min) | Chat adds suffix «سند مرتبط یافت نشد»; letter uses user fields |

| Orphan vectors | Full ingest runs `delete_orphan_sources` |



## Troubleshooting



| Issue | Action |

|-------|--------|

| embed HTTP 400 | Unload v1.5; use v2 only; verify `/v1/embeddings` |

| ingest pending | LM down — files saved; retry after Load embed model |

| PDF empty | Scanned PDF — no text layer; use OCR (future) or txt |

| Settings shows 0 سند | Upload or copy to `pmo_docs/` then refresh |



## API



- `POST /api/pmo/documents/upload` — multipart `files`

- `GET /api/pmo/documents/list`

- `DELETE /api/pmo/documents/{name}`

- `POST /api/pmo/ingest` — full re-index + orphan cleanup



Upload is **gateway-only** — n8n webhooks cover ingest/letter/risk only.


