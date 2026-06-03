# PMO AI — Build offline bundle

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$bundle = Join-Path $root "pmo-offline-bundle"
$images = Join-Path $bundle "images"
New-Item -ItemType Directory -Force -Path $images, (Join-Path $bundle "config"), (Join-Path $bundle "docs") | Out-Null

Write-Host "Building images..." -ForegroundColor Cyan
docker compose build
docker tag pmo_ai_system-lmstudio-gateway pmo-gateway:prod
docker tag pmo_ai_system-pmo-ui pmo-ui:prod

$ids = @(
    (docker images -q pmo-gateway:prod),
    (docker images -q pmo-ui:prod),
    (docker images -q mirror2.chabokan.net/n8nio/n8n:latest),
    (docker images -q mirror2.chabokan.net/qdrant/qdrant:latest),
    (docker images -q mirror2.chabokan.net/nginx:latest)
) | Where-Object { $_ }

foreach ($id in $ids) {
    $out = Join-Path $images "pmo-$id.tar"
    docker save -o $out $id
    Write-Host "Saved $out"
}

Copy-Item ".env.example" (Join-Path $bundle "config\.env.example") -Force
Copy-Item "config\models.yaml" (Join-Path $bundle "config\models.yaml") -Force
Copy-Item "scripts\install.ps1" (Join-Path $bundle "install.ps1") -Force
Copy-Item "scripts\setup_lmstudio.ps1" (Join-Path $bundle "setup_lmstudio.ps1") -Force
Copy-Item "scripts\preflight.ps1" (Join-Path $bundle "preflight.ps1") -Force
Copy-Item "scripts\bootstrap_n8n.ps1" (Join-Path $bundle "bootstrap_n8n.ps1") -Force
Copy-Item "docker-compose.prod.yml" (Join-Path $bundle "docker-compose.yml") -Force
Copy-Item "samples" (Join-Path $bundle "samples") -Recurse -Force
Copy-Item "docs\INSTALL_FA.md" (Join-Path $bundle "INSTALL_FA.md") -Force
Copy-Item "docs\ARCHITECTURE.md" (Join-Path $bundle "docs\ARCHITECTURE.md") -Force

Write-Host "Bundle ready: $bundle" -ForegroundColor Green
