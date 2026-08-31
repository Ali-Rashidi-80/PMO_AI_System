# PMO AI — Installation Guide (Persian)

[English](../INSTALL.md) · **فارسی**

## پیش‌نیاز

- Windows 10/11 + WSL2 + Docker Desktop
- LM Studio + GGUF models:
  - `gemma-4-e4b-it-ud`
  - `nomic-embed-text-v2`

## نصب (۹ گام)

1. `wsl --install` و reboot
2. Docker Desktop → WSL integration ON
3. LM Studio نصب + یک بار GUI باز شود
4. کپی GGUF به `%USERPROFILE%\.lmstudio\models\lmstudio-community\`
5. `.\scripts\setup_lmstudio.ps1` یا load دستی + Serve on Local Network
6. `Copy-Item .env.example .env` و ویرایش `WEBHOOK_SECRET`
7. `.\scripts\install.ps1`
8. `.\scripts\preflight.ps1`
9. مرورگر: **http://localhost:8080**

## بسته آفلاین

```powershell
.\scripts\build_bundle.ps1
# انتقال pmo-offline-bundle/ به سیستم هدف
cd pmo-offline-bundle
.\setup_lmstudio.ps1
.\install.ps1
```

## PoC

```powershell
.\scripts\run_poc.ps1
.\scripts\benchmark_pmo.py
```

## پورت‌ها

| سرویس | URL |
|---|---|
| UI | http://localhost:8080 |
| Gateway | internal :8081 |
| n8n admin | http://127.0.0.1:5678 |
| Qdrant | http://127.0.0.1:6333 |
