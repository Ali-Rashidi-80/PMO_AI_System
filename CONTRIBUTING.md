# Contributing to PMO AI System

Thank you for helping improve air-gapped PMO automation. English is the **canonical** language for issues and PRs; Persian companion docs (`.fa.md`) should track the same facts.

## Development setup

```powershell
Copy-Item .env.example .env
pip install -r services/lmstudio-gateway/requirements.txt `
            -r services/lmstudio-gateway/requirements-test.txt
python scripts/generate_fixtures.py
python -m pytest tests/unit tests/integration -m "not live" -q
```

Full stack (LM Studio + Docker):

```powershell
.\scripts\setup_lmstudio.ps1
.\scripts\install.ps1
.\scripts\preflight.ps1
```

## What to change where

| Area | Location |
|------|----------|
| Model IDs, RAG params | `config/models.yaml` (SSOT) |
| Prompts | `config/prompts/*.txt` |
| Gateway API | `services/lmstudio-gateway/` |
| RTL UI | `services/pmo-ui/` |
| n8n workflows | `Workflows/*.json` + `scripts/bootstrap_n8n.ps1` |
| Tests | `tests/unit`, `tests/integration`, `tests/playwright` |

After editing workflows, run:

```powershell
python scripts/validate_workflow.py Workflows
```

## Pull request guidelines

1. Keep changes **atomic** — one concern per PR when possible.
2. Run `python -m pytest tests/unit tests/integration -m "not live" -q` before opening.
3. Update **English** docs first; mirror factual changes in `.fa.md` companions.
4. Never commit `.env`, `n8n_data/`, `qdrant_data/`, or user documents.
5. Do not change model IDs in code — only in `config/models.yaml`.
6. Run `.\scripts\scan_secrets.ps1` before pushing to GitHub.

## Commit messages

Use imperative mood, present tense:

- `fix gateway auth on empty token`
- `docs: add offline bundle runbook`
- `test: cover upload batch limit`

## Reporting issues

Include: OS, Docker version, LM Studio model list (`GET /v1/models`), `preflight.ps1` output, and relevant gateway logs.

See also [SECURITY.md](SECURITY.md) for vulnerability reporting.

[فارسی](CONTRIBUTING.fa.md)
