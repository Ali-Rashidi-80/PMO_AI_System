# PMO AI — End-to-end PoC runner

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
$envContent = Get-Content ".env" -Raw
if ($envContent -match 'WEBHOOK_SECRET=(.+)' ) { $token = $matches[1].Trim() } else { $token = "change-me-pmo-secret-2026" }
$headers = @{ "X-PMO-Token" = $token; "Content-Type" = "application/json" }

Write-Host "Step 1: Preflight" -ForegroundColor Cyan
& "$root\scripts\preflight.ps1"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "Step 2: Stack up" -ForegroundColor Cyan
docker compose up -d --build
Start-Sleep -Seconds 25

Write-Host "Step 3: Ingest" -ForegroundColor Cyan
$ingest = Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/pmo/ingest" -Headers $headers
Write-Host ($ingest | ConvertTo-Json -Depth 5)

Write-Host "Step 4: Letter" -ForegroundColor Cyan
$letter = Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/pmo/letter" -Headers $headers -Body '{"contractor_name":"پیمانکار الف","delay_subject":"تأخیر فاز ۳"}'
Write-Host ($letter | ConvertTo-Json -Depth 5)

Write-Host "Step 5: Risk" -ForegroundColor Cyan
$risk = Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/pmo/risk/run" -Headers $headers
Write-Host "Risk status: $($risk.status)"

Write-Host "Step 6: Chat smoke" -ForegroundColor Cyan
$chat = Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/pmo/chat" -Headers $headers -Body '{"prompt":"سلام","use_rag":false}'
Write-Host "Chat status: $($chat.status)"

Write-Host "Step 7: Documents list" -ForegroundColor Cyan
$docs = Invoke-RestMethod -Method GET -Uri "http://localhost:8080/api/pmo/documents/list" -Headers $headers
Write-Host "Documents: $($docs.files.Count)"

Write-Host "Step 8: Upload smoke" -ForegroundColor Cyan
$boundary = [System.Guid]::NewGuid().ToString()
$bodyLines = @(
    "--$boundary",
    'Content-Disposition: form-data; name="files"; filename="poc_upload.txt"',
    'Content-Type: text/plain',
    '',
    ('بند قرارداد تأخیر جریمه. ' * 5),
    "--$boundary--"
) -join "`r`n"
$uploadHeaders = @{
    "X-PMO-Token" = $token
    "Content-Type" = "multipart/form-data; boundary=$boundary"
}
try {
    $up = Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/pmo/documents/upload" -Headers $uploadHeaders -Body $bodyLines
    Write-Host "Upload saved: $($up.saved)"
} catch {
    Write-Host "Upload skipped: $_" -ForegroundColor Yellow
}

Write-Host "`nPoC run complete — http://localhost:8080" -ForegroundColor Green
