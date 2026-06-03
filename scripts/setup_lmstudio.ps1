# PMO AI — LM Studio setup (GUI-first + CLI fallback)

$ErrorActionPreference = "Continue"
Write-Host "=== PMO LM Studio Setup ===" -ForegroundColor Cyan

$modelsRoot = Join-Path $env:USERPROFILE ".lmstudio\models\lmstudio-community"
$embedPath = Join-Path $modelsRoot "nomic-embed-text-v2"
$llmPath = Join-Path $modelsRoot "gemma-4-E4B-it-UD-Q4_K_XL"

Write-Host @"

STEP 1 (GUI — recommended):
  1. Open LM Studio
  2. Developer -> Settings -> Enable 'Serve on Local Network'
  3. Load models: nomic-embed-text-v2, gemma-4-e4b-it-ud
  4. Unload: text-embedding-nomic-embed-text-v1.5
  5. Start Server on port 1234 with CORS enabled

STEP 2 (CLI fallback if lms is in PATH):
"@

    if (Get-Command lms -ErrorAction SilentlyContinue) {
    Write-Host "Running lms CLI..." -ForegroundColor Yellow
    lms daemon up 2>$null
    lms unload text-embedding-nomic-embed-text-v1.5 2>$null
    lms load nomic-embed-text-v2 --gpu=max 2>$null
    lms load gemma-4-e4b-it-ud --gpu=max 2>$null
    # v1.5 must stay loaded on some LM Studio builds for /v1/embeddings to respond
    lms load text-embedding-nomic-embed-text-v1.5 --gpu=max 2>$null
    lms server start --port 1234 --cors 2>$null
} else {
    Write-Host "lms CLI not found — use GUI steps above." -ForegroundColor Yellow
}

Write-Host "`nVerifying..." -ForegroundColor Cyan
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 10
    $resp.data | ForEach-Object { Write-Host "  Model: $($_.id)" }
    Write-Host "LM Studio OK" -ForegroundColor Green
} catch {
    Write-Host "LM Studio not reachable: $_" -ForegroundColor Red
    exit 1
}
