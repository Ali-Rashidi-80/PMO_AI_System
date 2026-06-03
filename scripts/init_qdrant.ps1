# Ensure Qdrant collection exists for RAG

$ErrorActionPreference = "Stop"
$url = "http://127.0.0.1:6333/collections/pmo_knowledge_base"
try {
    Invoke-RestMethod -Uri $url -TimeoutSec 5 | Out-Null
    Write-Host "Qdrant collection pmo_knowledge_base exists."
} catch {
    $body = '{"vectors":{"size":768,"distance":"Cosine"}}'
    Invoke-RestMethod -Method PUT -Uri $url -ContentType "application/json" -Body $body | Out-Null
    Write-Host "Created Qdrant collection pmo_knowledge_base."
}
