# PMO AI — Acceptance Checklist (40 items)

Run after `install.ps1` + LM Studio models loaded. Mark PASS/FAIL per item.

## Environment (1–8)

| # | Check | PASS |
|---|---|---|
| 1 | WSL2 enabled | |
| 2 | Docker Desktop running | |
| 3 | LM Studio Serve on Local Network ON | |
| 4 | `gemma-4-e4b-it-ud` loaded | |
| 5 | `nomic-embed-text-v2` loaded | |
| 6 | v1.5 embedding unloaded | |
| 7 | `.env` copied from `.env.example` | |
| 8 | `preflight.ps1` ALL PASS | |

## Docker stack (9–16)

| # | Check | PASS |
|---|---|---|
| 9 | `docker compose up -d` succeeds | |
| 10 | `pmo_qdrant` running | |
| 11 | `pmo_lmstudio_gateway` healthy | |
| 12 | `pmo_n8n` running | |
| 13 | `pmo_ui` running | |
| 14 | `pmo_nginx` on :8080 | |
| 15 | Container→host LM Studio OK | |
| 16 | n8n bootstrap imported workflows | |

## Gateway (17–22)

| # | Check | PASS |
|---|---|---|
| 17 | `GET /health` returns status | |
| 18 | `GET /v1/models` lists 2 ids | |
| 19 | Chat completions works | |
| 20 | Embeddings works | |
| 21 | Invalid token → 401 on `/api/pmo/*` | |
| 22 | DOCX endpoint returns file | |

## Workflows (23–30)

| # | Check | PASS |
|---|---|---|
| 23 | WF-01 no Unknown nodes | |
| 24 | WF-02 no Unknown nodes | |
| 25 | WF-03 no Unknown nodes | |
| 26 | Ingest populates Qdrant | |
| 27 | Letter returns Persian text | |
| 28 | Letter auth failure clean JSON | |
| 29 | Risk returns HTML + JSON | |
| 30 | Risk failed only when reports **and** context both empty | |
| 30b | Document upload txt/docx/pdf works | |
| 30c | `GET /api/pmo/documents/list` returns files | |

## UI (31–38)

| # | Check | PASS |
|---|---|---|
| 31 | `http://localhost:8080` RTL dashboard — 5 tabs | |
| 32 | Chat stream + RAG checkbox | |
| 33 | Letter form + free_prompt + docx download | |
| 34 | Risk table + context field | |
| 35 | Docs upload zone + ingest + document table | |
| 36 | Settings status cards + n8n webhooks | |
| 37 | Theme toggle + tour | |
| 38 | `pytest -m "not live"` PASS | |

## Security / Air-gap (36–38)

| # | Check | PASS |
|---|---|---|
| 36 | No outbound proxy in gateway | |
| 37 | Source not mounted in prod compose | |
| 38 | Webhook secret enforced | |

## Benchmark / Docs (39–40)

| # | Check | PASS |
|---|---|---|
| 39 | `benchmark_pmo.py` produces CSV/MD | |
| 40 | Article appendix matches measured KPIs | |

**Sign-off:** ___ / 40 PASS — Date: ___
