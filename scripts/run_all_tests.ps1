# PMO AI — Unified test runner
param([switch]$Live)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "=== PMO run_all_tests ===" -ForegroundColor Cyan

& "$root\scripts\preflight.ps1" -SkipLM
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "Generate fixtures" -ForegroundColor Cyan
python scripts/generate_fixtures.py

Write-Host "Install test deps" -ForegroundColor Cyan
pip install -q -r services/lmstudio-gateway/requirements.txt -r services/lmstudio-gateway/requirements-test.txt

$env:WEBHOOK_SECRET = "change-me-pmo-secret-2026"

Write-Host "pytest (unit + integration, not live)" -ForegroundColor Cyan
python -m pytest tests/unit tests/integration -m "not live" -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "docker compose (for Playwright)" -ForegroundColor Cyan
docker compose up -d --build
Start-Sleep -Seconds 20

Push-Location "$root\tests\playwright"
if (-not (Test-Path "node_modules")) { npm install --silent }
# Use system Chrome (channel: chrome in playwright.config.ts) — no bundled browser download
npx playwright test
$pwExit = $LASTEXITCODE
Pop-Location
if ($pwExit -ne 0) { exit $pwExit }

if ($Live) {
    & "$root\scripts\preflight.ps1"
    if ($LASTEXITCODE -eq 0) {
        python -m pytest tests -m live -q
        $env:PMO_LIVE = "1"
        Push-Location "$root\tests\playwright"
        npx playwright test --project=chrome --grep "@golden"
        Pop-Location
    }
}

Write-Host "Done — see docs/test_matrix.md" -ForegroundColor Green
