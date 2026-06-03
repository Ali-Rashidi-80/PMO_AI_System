# PMO AI — Preflight checks (PowerShell)
param([switch]$SkipLM)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "=== PMO Preflight ===" -ForegroundColor Cyan

function Test-Step($name, [scriptblock]$block) {
    try {
        & $block
        Write-Host "[PASS] $name" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "[FAIL] $name — $_" -ForegroundColor Red
        return $false
    }
}

$results = @()
$results += Test-Step "Docker" { docker version | Out-Null }

if (-not $SkipLM) {
    $results += Test-Step "LM Studio host" {
        Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 5 | Out-Null
    }
    $results += Test-Step "Models gemma+embed" {
        $m = (Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 5).data.id
        if ($m -notcontains "gemma-4-e4b-it-ud") { throw "gemma-4-e4b-it-ud missing" }
        if ($m -notcontains "nomic-embed-text-v2") { throw "nomic-embed-text-v2 missing" }
    }
    $results += Test-Step "Docker->host LM Studio" {
        docker run --rm mirror2.chabokan.net/curlimages/curl:latest -sf http://host.docker.internal:1234/v1/models | Out-Null
    }
} else {
    Write-Host "[SKIP] LM Studio checks (-SkipLM)" -ForegroundColor Yellow
}

$results += Test-Step "Workflow JSON" {
    python scripts/validate_workflow.py Workflows
    if ($LASTEXITCODE -ne 0) { throw "validate failed" }
}
$results += Test-Step "pmo_docs samples" {
    if (-not (Test-Path "pmo_docs\contract_clause_sample.txt")) {
        if (-not (Test-Path "pmo_docs\contract_full_fa.txt")) { throw "missing sample" }
    }
}
$results += Test-Step "Gateway health (if up)" {
    try {
        Invoke-RestMethod -Uri "http://localhost:8081/health" -TimeoutSec 3 | Out-Null
    } catch {
        Write-Host "  (gateway not running — skip)" -ForegroundColor Yellow
    }
}
$results += Test-Step "UI entry (if up)" {
    try {
        Invoke-WebRequest -Uri "http://localhost:8080/" -TimeoutSec 3 -UseBasicParsing | Out-Null
    } catch {
        Write-Host "  (stack not running — skip)" -ForegroundColor Yellow
    }
}

if ($results -contains $false) {
    Write-Host "`nPreflight FAILED" -ForegroundColor Red
    exit 1
}
Write-Host "`nPreflight ALL PASS" -ForegroundColor Green
