# PMO AI — Import n8n workflows and credentials (run after stack is up)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "Waiting for n8n..." -ForegroundColor Cyan
for ($i = 0; $i -lt 60; $i++) {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:5678/healthz" -TimeoutSec 3 | Out-Null
        Start-Sleep -Seconds 5
        break
    } catch {
        Start-Sleep -Seconds 3
    }
}

Write-Host "Importing credentials..." -ForegroundColor Cyan
docker exec pmo_n8n n8n import:credentials --input=/bootstrap/credentials.json

Write-Host "Importing workflows..." -ForegroundColor Cyan
docker exec pmo_n8n n8n import:workflow --separate --input=/bootstrap/workflows/

Write-Host "Publishing workflows..." -ForegroundColor Cyan
$list = docker exec pmo_n8n n8n list:workflow 2>$null
foreach ($line in ($list -split "`n")) {
    if ($line -match '^([A-Za-z0-9]+)\|') {
        $id = $matches[1]
        docker exec pmo_n8n n8n publish:workflow --id=$id 2>$null
    }
}

Write-Host "Restarting n8n to apply published workflows..." -ForegroundColor Cyan
docker compose restart pmo-n8n | Out-Null
Start-Sleep -Seconds 20

Write-Host "Bootstrap complete." -ForegroundColor Green
