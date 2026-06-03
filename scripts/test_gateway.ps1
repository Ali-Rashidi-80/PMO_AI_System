# PMO Gateway smoke tests (Phase 1 gate)

$ErrorActionPreference = "Stop"
$base = if ($env:GATEWAY_URL) { $env:GATEWAY_URL } else { "http://127.0.0.1:8081" }

Write-Host "Gateway tests -> $base" -ForegroundColor Cyan

$h = Invoke-RestMethod "$base/health"
if ($h.status -ne "up") { throw "health failed" }
Write-Host "[PASS] health"

$models = (Invoke-RestMethod "$base/v1/models").data.id
if ($models -notcontains "gemma-4-e4b-it-ud") { throw "gemma missing" }
Write-Host "[PASS] models"

$chat = Invoke-RestMethod -Method POST -Uri "$base/v1/chat/completions" -ContentType "application/json" -Body '{"model":"gemma-4-e4b-it-ud","messages":[{"role":"user","content":"ping"}],"max_tokens":16}'
if (-not $chat.choices[0].message.content) { throw "chat empty" }
Write-Host "[PASS] chat"

try {
    $emb = Invoke-RestMethod -Method POST -Uri "$base/v1/embeddings" -ContentType "application/json" -Body '{"model":"nomic-embed-text-v2","input":"test"}'
    if ($emb.data[0].embedding.Count -lt 1) { throw "embed empty" }
    Write-Host "[PASS] embed"
} catch {
    Write-Host "[WARN] embed v2 failed - unload v1.5 and verify LM Studio embed API" -ForegroundColor Yellow
}

Write-Host "Gateway gate complete." -ForegroundColor Green
