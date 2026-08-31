# معماری PMO AI

## استک

```
Browser → nginx:8080 → pmo-ui | lmstudio-gateway:8081 | pmo-n8n:5678
lmstudio-gateway → LM Studio (host:1234)
pmo-n8n → gateway + qdrant:6333
```

## مدل‌ها (SSOT: config/models.yaml)

- LLM: `gemma-4-e4b-it-ud`
- Embedding: `nomic-embed-text-v2`

## Workflowها

| فایل | Webhook |
|------|---------|
| 01_rag_ingestion.json | POST /webhook/pmo/ingest |
| 02_scenario_a_letter.json | POST /webhook/pmo/letter |
| 03_scenario_b_risk.json | POST /webhook/pmo/risk |

## نگاشت مقاله

ادعاهای مقاله برای Qwen 26B / nomic v1.5 با مدل‌های PoC بالا جایگزین شده‌اند.

## مسئولیت اجزا

| سرویس | پورت (توسعه) | نقش |
|-------|--------------|-----|
| nginx | 8080 (عمومی) | پروکسی معکوس، آپلود ۵۰ مگابایت |
| pmo-ui | 3000 (داخلی) | داشبورد RTL استاتیک |
| lmstudio-gateway | 8081 (داخلی) | FastAPI BFF، RAG، API اسناد |
| pmo-n8n | 5678 (localhost) | موتور workflow |
| pmo-qdrant | 6333 (localhost) | ذخیره برداری |

## رفتار در شرایط افت

| سرویس قطع | رفتار |
|-----------|-------|
| LM Studio | `ready=false`؛ شکست تدریجی chat/letter/risk |
| Qdrant | آپلود ذخیره؛ ingest ممکن است شکست بخورد |
| n8n | API مستقیم gateway کار می‌کند |
| آپلود بدون ingest | manifest با `pending_ingest` |

[English](ARCHITECTURE.md) · [README.fa.md](../README.fa.md)
