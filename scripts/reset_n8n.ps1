# PMO AI — Reset n8n and import workflows once

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "Stopping n8n and clearing data volume..." -ForegroundColor Yellow
docker compose stop pmo-n8n
docker compose rm -f pmo-n8n
docker volume rm pmo_ai_system_n8n_data -f

Write-Host "Starting n8n..." -ForegroundColor Cyan
docker compose up -d pmo-n8n

Write-Host "Waiting for n8n migrations (60s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

& "$root\scripts\bootstrap_n8n.ps1"
