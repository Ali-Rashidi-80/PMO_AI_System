# مشارکت در PMO AI System

از مشارکت شما در بهبود اتوماسیون PMO آفلاین سپاسگزاریم. زبان **مرجع** برای issue و PR انگلیسی است؛ مستندات فارسی (`.fa.md`) باید همان حقایق را منعکس کنند.

## راه‌اندازی توسعه

```powershell
Copy-Item .env.example .env
pip install -r services/lmstudio-gateway/requirements.txt `
            -r services/lmstudio-gateway/requirements-test.txt
python scripts/generate_fixtures.py
python -m pytest tests/unit tests/integration -m "not live" -q
```

استک کامل (LM Studio + Docker):

```powershell
.\scripts\setup_lmstudio.ps1
.\scripts\install.ps1
.\scripts\preflight.ps1
```

## نگاشت تغییرات

| حوزه | مسیر |
|------|------|
| شناسه مدل‌ها، پارامتر RAG | `config/models.yaml` (SSOT) |
| پرامپت‌ها | `config/prompts/*.txt` |
| API گیت‌وی | `services/lmstudio-gateway/` |
| رابط RTL | `services/pmo-ui/` |
| workflowهای n8n | `Workflows/*.json` + `scripts/bootstrap_n8n.ps1` |
| تست‌ها | `tests/unit`, `tests/integration`, `tests/playwright` |

پس از ویرایش workflow:

```powershell
python scripts/validate_workflow.py Workflows
```

## راهنمای Pull Request

1. تغییرات **اتمیک** — هر PR یک موضوع.
2. قبل از باز کردن PR: `python -m pytest tests/unit tests/integration -m "not live" -q`
3. ابتدا مستندات **انگلیسی**؛ سپس `.fa.md` متناظر.
4. هرگز `.env`، `n8n_data/`، `qdrant_data/` یا اسناد کاربر commit نشود.
5. شناسه مدل فقط در `config/models.yaml` تغییر کند.

## گزارش مشکل

شامل: سیستم‌عامل، نسخه Docker، لیست مدل LM Studio، خروجی `preflight.ps1` و لاگ گیت‌وی.

[English](CONTRIBUTING.md) · [SECURITY.fa.md](SECURITY.fa.md)
