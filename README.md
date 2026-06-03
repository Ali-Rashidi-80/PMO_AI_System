# PMO AI — Zero-Trust Local Automation

Air-gapped PMO knowledge automation: **n8n + Qdrant + LM Studio Gateway + Persian UI**.

## Quick start

```powershell
Copy-Item .env.example .env
.\scripts\setup_lmstudio.ps1
.\scripts\install.ps1
# Open http://localhost:8080
```

## Structure

- `services/lmstudio-gateway/` — OpenAI proxy + BFF (from pc_client patterns)
- `services/pmo-ui/` — RTL web UI
- `services/nginx/` — entry :8080
- `Workflows/` — n8n exports (01/02/03)
- `config/models.yaml` — single source of truth
- `scripts/` — install, preflight, run_poc, benchmark

## Docs

- [INSTALL_FA.md](docs/INSTALL_FA.md)
- [ARCHITECTURE.md](docs/ARCHITECTURE.md)

Legacy files archived under `archive/`.
