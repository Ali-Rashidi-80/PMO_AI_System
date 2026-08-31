# PMO AI — Installation Guide

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Windows 10/11 | Primary platform |
| WSL2 | Required by Docker Desktop |
| Docker Desktop | WSL integration enabled |
| LM Studio | Local GGUF inference |
| Models | `gemma-4-e4b-it-ud` (LLM) + `nomic-embed-text-v2` (embeddings) |

## Install (9 steps)

1. `wsl --install` and reboot
2. Docker Desktop → Settings → WSL integration **ON**
3. Install LM Studio; open GUI once
4. Copy GGUF files to `%USERPROFILE%\.lmstudio\models\lmstudio-community\`
5. `.\scripts\setup_lmstudio.ps1` — or load models manually + **Serve on Local Network**
6. `Copy-Item .env.example .env` — edit `WEBHOOK_SECRET`
7. `.\scripts\install.ps1` — build stack, init Qdrant, bootstrap n8n
8. `.\scripts\preflight.ps1` — all checks green
9. Browser: **http://localhost:8080**

## Offline bundle

```powershell
.\scripts\build_bundle.ps1
# Transfer pmo-offline-bundle/ to target machine
cd pmo-offline-bundle
.\setup_lmstudio.ps1
.\install.ps1
```

## Proof of concept

```powershell
.\scripts\run_poc.ps1
python scripts/benchmark_pmo.py
```

## Ports

| Service | URL |
|---------|-----|
| UI (entry) | http://localhost:8080 |
| Gateway (internal) | :8081 |
| n8n admin | http://127.0.0.1:5678 |
| Qdrant | http://127.0.0.1:6333 |
| LM Studio | http://127.0.0.1:1234 |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Gateway unhealthy | Confirm LM Studio serving on :1234; check `LMSTUDIO_UPSTREAM` |
| Empty RAG results | Load embed model → ingest → switch to LLM model |
| n8n workflows missing | `.\scripts\bootstrap_n8n.ps1` or `.\scripts\reset_n8n.ps1` |
| Docker→host LM fails | Docker Desktop → `host.docker.internal` enabled |

[فارسی](docs/INSTALL_FA.md) · [Architecture](docs/ARCHITECTURE.md)
