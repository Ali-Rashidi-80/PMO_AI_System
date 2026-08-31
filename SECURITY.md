# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` branch | ✅ Active development |
| Offline bundles tagged `pmo-offline-bundle/*` | ✅ While deployed |

## Reporting a vulnerability

**Do not** open public GitHub issues for security vulnerabilities.

Email maintainers with:

1. Description and impact
2. Steps to reproduce
3. Affected component (`gateway`, `n8n`, `nginx`, `ui`, workflows)
4. Suggested fix (optional)

We aim to acknowledge within **5 business days**.

## Threat model (design intent)

PMO AI is built for **air-gapped / zero-trust local** deployment:

| Control | Implementation |
|---------|----------------|
| No outbound LLM proxy | Gateway talks only to `LMSTUDIO_UPSTREAM` (host LM Studio) |
| Webhook auth | `X-PMO-Token` header = `WEBHOOK_SECRET` from `.env` |
| n8n admin bound | `127.0.0.1:5678` in dev compose |
| Prod source isolation | `docker-compose.prod.yml` — no gateway source mounts |
| Upload limits | 30 MB/file, 10 files/batch; `.exe` rejected |
| Secrets not in repo | `.env` gitignored; rotate `WEBHOOK_SECRET` before production |

## Hardening checklist (operators)

- [ ] Change default `WEBHOOK_SECRET` and `N8N_BASIC_AUTH_PASSWORD`
- [ ] Use strong `N8N_ENCRYPTION_KEY` (`openssl rand -hex 16`)
- [ ] Keep LM Studio on local network only
- [ ] Do not expose `:5678` or `:6333` beyond localhost
- [ ] Review `pmo_docs/` permissions on shared hosts

## Dependency updates

Dependabot monitors pip, npm (Playwright), and GitHub Actions. Review CI before merging major bumps.

## Before publishing to GitHub

Run locally:

```powershell
.\scripts\scan_secrets.ps1
.\scripts\preflight.ps1 -SkipLM
python -m pytest tests/unit tests/integration -m "not live" -q
```

**Never commit:** `.env`, `n8n_data/`, `qdrant_data/`, user PDFs/DOCX in `pmo_docs/`, `.cursor/` plans, `archive/0/` chat logs.

**Dev placeholders (safe in repo):** `change-me-pmo-secret-2026` in `.env.example`, workflows, and tests — rotate via `.env` + `scripts/sync_n8n_secret.ps1` before production.

`credentials.json` uses LM Studio dummy key `lm-studio` (not a real secret).

[فارسی](SECURITY.fa.md)
