# سیاست امنیتی

## نسخه‌های پشتیبانی‌شده

| نسخه | پشتیبانی |
|------|----------|
| شاخه `main` | ✅ توسعه فعال |
| بسته‌های آفلاین `pmo-offline-bundle/*` | ✅ در زمان استقرار |

## گزارش آسیب‌پذیری

**از** باز کردن issue عمومی در GitHub **خودداری** کنید.

ایمیل به نگهدارندگان با:

1. شرح و اثر
2. مراحل بازتولید
3. اجزای متأثر (`gateway`, `n8n`, `nginx`, `ui`, workflowها)
4. پیشنهاد رفع (اختیاری)

هدف: پاسخ ظرف **۵ روز کاری**.

## مدل تهدید (طراحی)

PMO AI برای استقرار **آفلاین / zero-trust محلی** ساخته شده:

| کنترل | پیاده‌سازی |
|-------|-----------|
| بدون پروکسی خروجی LLM | گیت‌وی فقط به `LMSTUDIO_UPSTREAM` (LM Studio میزبان) |
| احراز webhook | هدر `X-PMO-Token` = `WEBHOOK_SECRET` از `.env` |
| n8n محدود به localhost | `127.0.0.1:5678` در compose توسعه |
| جداسازی سورس در prod | `docker-compose.prod.yml` — بدون mount سورس گیت‌وی |
| محدودیت آپلود | ۳۰ مگابایت/فایل، ۱۰ فایل/دسته؛ رد `.exe` |
| رازها در repo نیست | `.env` در gitignore؛ چرخش `WEBHOOK_SECRET` قبل از production |

## چک‌لیست سخت‌سازی (اپراتور)

- [ ] تغییر `WEBHOOK_SECRET` و `N8N_BASIC_AUTH_PASSWORD` پیش‌فرض
- [ ] `N8N_ENCRYPTION_KEY` قوی (`openssl rand -hex 16`)
- [ ] LM Studio فقط شبکه محلی
- [ ] عدم expose `:5678` و `:6333` فراتر از localhost
- [ ] بررسی مجوزهای `pmo_docs/` روی میزبان مشترک

## قبل از انتشار در GitHub

```powershell
.\scripts\scan_secrets.ps1
.\scripts\preflight.ps1 -SkipLM
python -m pytest tests/unit tests/integration -m "not live" -q
```

**هرگز commit نشود:** `.env`، `n8n_data/`، `qdrant_data/`، PDF/DOCX کاربر، `.cursor/`، `archive/0/`.

**placeholderهای توسعه:** `change-me-pmo-secret-2026` — قبل از production چرخش دهید.

[English](SECURITY.md)
