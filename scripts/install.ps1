# PMO AI — Install / start stack

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example — edit WEBHOOK_SECRET before production."
}

Write-Host "Building and starting PMO stack..." -ForegroundColor Cyan
docker compose build
docker compose up -d

Write-Host "Waiting for health..." -ForegroundColor Yellow
Start-Sleep -Seconds 25
& "$root\scripts\init_qdrant.ps1"
& "$root\scripts\bootstrap_n8n.ps1"
try {
    $h = Invoke-RestMethod -Uri "http://localhost:8080/health" -TimeoutSec 10
    Write-Host "Health: $($h | ConvertTo-Json -Compress)"
} catch {
    Write-Host "Health check pending — run scripts/preflight.ps1"
}

Write-Host "`nOpen http://localhost:8080" -ForegroundColor Green
