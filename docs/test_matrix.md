# PMO Test Matrix

Run: `.\scripts\run_all_tests.ps1` (tier 0) or `.\scripts\run_all_tests.ps1 -Live` (LM + golden)

## Tier 0 — Unit (mock, no LM)

| ID | Case | Module | Auto | Expected |
|----|------|--------|------|----------|
| U01 | chunk overlap | rag | yes | PASS |
| U02 | chunk empty | rag | yes | PASS |
| U03 | format_context empty/hits | rag | yes | PASS |
| U04 | file_hash stable | rag | yes | PASS |
| U05 | ingest missing dir | rag | yes | PASS |
| U06 | delete_by_source Qdrant | rag | yes | PASS |
| U07 | is_supported L1/L2 | loader | yes | PASS |
| U08 | is_rejected exe | loader | yes | PASS |
| U09 | normalize_persian | loader | yes | PASS |
| U10 | extract empty txt | loader | yes | PASS |
| U11 | read_documents skip empty | loader | yes | PASS |
| U12 | fixture contract_full_fa | loader | yes | PASS |
| U13 | clean strict/non-strict | loader | yes | PASS |
| U14 | sanitize think strip | pmo_service | yes | PASS |
| U15 | sanitize ERROR_NO_DOCS | pmo_service | yes | PASS |
| U16 | parse risk JSON | pmo_service | yes | PASS |
| U17 | chat empty error | pmo_service | yes | PASS |
| U18 | letter free-only | pmo_service | yes | PASS |
| U19 | letter no fields failed | pmo_service | yes | PASS |

## Tier 1 — API (TestClient mock LM)

| ID | Endpoint | Case | Auto | Expected |
|----|----------|------|------|----------|
| A01 | GET /health | 200 | yes | PASS |
| A02 | GET /api/pmo/status | documents_count field | yes | PASS |
| A03 | POST /api/pmo/chat | empty → failed 200 | yes | PASS |
| A04 | POST /api/pmo/chat/stream | empty → 400 | yes | PASS |
| A05 | POST /api/pmo/chat | invalid token 401 | yes | PASS |
| A06 | POST /api/pmo/letter | free-only success | yes | PASS |
| A07 | POST /api/pmo/letter/docx | empty → 400 | yes | PASS |
| A08 | POST /api/pmo/risk/run | context-only success | yes | PASS |
| A09 | POST /api/pmo/risk/run | empty → failed | yes | PASS |
| A10 | POST /api/pmo/ingest | empty dir status | yes | PASS |
| A11 | GET /api/pmo/documents/list | auth + success | yes | PASS |
| A12 | POST /api/pmo/documents/upload | txt saved | yes | PASS |
| A13 | POST /api/pmo/documents/upload | exe rejected | yes | PASS |
| A14 | DELETE /api/pmo/documents/{name} | missing → 404 | yes | PASS |
| A15 | GET /api/pmo/status | LM down → ready false | yes | PASS |
| A16 | GET /health | qdrant/n8n fields | yes | PASS |
| A17 | POST upload | saves without auto-ingest | yes | PASS |

## Tier 2 — Playwright (mock API, system Chrome)

| ID | Tab | Case | Auto | Expected |
|----|-----|------|------|----------|
| P01 | Chat | empty validation | yes | PASS |
| P02 | Chat | stream mock | yes | PASS |
| P03 | Letter | validation empty | yes | PASS |
| P04 | Letter | free prompt (details open) | yes | PASS |
| P05 | Risk | table after run | yes | PASS |
| P06 | Docs | ingest button | yes | PASS |
| P07 | Docs | drop zone visible | yes | PASS |
| P08 | Settings | status cards (آنلاین) | yes | PASS |
| P09 | Settings | theme toggle | yes | PASS |
| P10 | Cross | #ingest → docs panel | yes | PASS |
| P11 | Cross | RTL dir=rtl | yes | PASS |

## Tier 3 — n8n parity (stack on :8080)

| ID | Path | Case | Auto | Tier |
|----|------|------|------|------|
| N01 | /api/pmo/n8n/ingest | bad token 401 | yes | 0 |
| N02 | /webhook/pmo/ingest | JSON status key | yes | 1 (stack) |
| N03 | gateway vs n8n ingest | shape parity | yes | 1 (stack) |
| N04 | /webhook/pmo/letter | JSON status | yes | live |
| N05 | /webhook/pmo/risk | JSON status | yes | live |

Upload API is **gateway-only** — not in n8n parity scope.

## Tier 4 — Live (optional `-Live`, LM Studio :1234)

| ID | Case | Auto | Requires |
|----|------|------|----------|
| L01 | status ready | yes | LM + stack |
| L02 | chat no RAG | yes | LM |
| L03 | letter free_prompt | yes | LM |
| L04 | risk with context | yes | LM |
| L05 | upload → ingest → chat RAG | yes | LM embed+LLM |
| L06 | Playwright @golden chat | yes | PMO_LIVE=1 |
| L07 | Playwright @golden letter | yes | PMO_LIVE=1 |

## Degradation (documented + tested)

| Service down | Behavior | Test |
|--------------|----------|------|
| LM Studio | status ready=false; chat fails gracefully | A15 |
| Qdrant | upload saves; ingest may fail | A17, runbook |
| n8n | gateway direct API still works | ARCHITECTURE |
| Upload without ingest | manifest status saved/pending_ingest | A17 |

## Manual / out of scope phase 1

| ID | Case | Notes |
|----|------|-------|
| M01 | PDF scan-only skip | fixture scan_only.pdf |
| M02 | 30MB boundary upload | manual |
| M03 | 10-file batch limit | manual |
| M04 | OCR / HTML / EPUB | L3 watch list |
| M05 | BM25 hybrid | future |
| M06 | Chunk A/B benchmark | benchmark_pmo.py |

## Sign-off

| Run date | pytest `-m "not live"` | playwright chrome | live `-Live` |
|----------|------------------------|-------------------|--------------|
| 2026-06-02 | 42 passed, 7 deselected (live) | 12 passed (+2 golden skip) | optional `-Live` |

Commands:

```powershell
python -m pytest tests/unit tests/integration -m "not live" -q
cd tests\playwright; npx playwright test --project=chrome
.\scripts\run_all_tests.ps1 -Live   # LM Studio required
```
