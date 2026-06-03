# PMO AI Architecture

## Stack

```
Browser → nginx:8080 → pmo-ui | lmstudio-gateway:8081 | pmo-n8n:5678
lmstudio-gateway → LM Studio (host:1234)
pmo-n8n → gateway + qdrant:6333
```

## Models (SSOT: config/models.yaml)

- LLM: `gemma-4-e4b-it-ud`
- Embedding: `nomic-embed-text-v2`

## Workflows

| File | Webhook |
|---|---|
| 01_rag_ingestion.json | POST /webhook/pmo/ingest |
| 02_scenario_a_letter.json | POST /webhook/pmo/letter |
| 03_scenario_b_risk.json | POST /webhook/pmo/risk |

## Article mapping

Article claims for Qwen 26B / nomic v1.5 are superseded by actual PoC models above.
