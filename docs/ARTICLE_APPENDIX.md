# Appendix — Article vs PoC Mapping

## Model corrections

| Article claim | PoC reality |
|---|---|
| Qwen 3.6 26B MoE | **Gemma 4 E4B** (`gemma-4-e4b-it-ud`) |
| nomic-embed-text v1.5 | **nomic-embed-text-v2** |
| Dual-LLM routing | Single LLM for both scenarios |

## Architecture corrections

- **Entry:** `http://localhost:8080` (nginx) — not n8n admin UI
- **LM Studio path:** n8n → gateway → `host.docker.internal:1234` (not `localhost:1234` inside Docker)
- **Remote Bridge:** not used — local air-gap only
- **Gateway:** extracted from `pc_client/main.py` patterns (httpx, semaphore, 900s timeout)

## KPI policy

Replace article tables with values from `docs/benchmark_results.md` only. Do not cite 96%/97% without measurement.

## Temperature (verified in workflows)

| Scenario | Temperature |
|---|---|
| A — Legal letter | 0.1 |
| B — Risk analysis | 0.3 |

## Deployment stack

Windows + WSL2 + Docker Desktop + LM Studio GUI-first load + offline bundle (`pmo-offline-bundle/`).

## Known environment note

`nomic-embed-text-v2` may return HTTP 400 on `/v1/embeddings` in some LM Studio builds while `text-embedding-nomic-embed-text-v1.5` still responds. Unload v1.5 and verify embed API before RAG ingest. KPI numbers must come from `benchmark_pmo.py` only.

- OpenAI credential: `responsesApi: false`
- SQLite n8n (PoC scope) — Postgres deferred to v2
