# Sync WEBHOOK_SECRET from .env into n8n workflow JSON files
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$secret = "change-me-pmo-secret-2026"
if (Test-Path ".env") {
    $m = Select-String -Path ".env" -Pattern '^WEBHOOK_SECRET=(.+)$'
    if ($m) { $secret = $m.Matches[0].Groups[1].Value.Trim() }
}

Get-ChildItem "Workflows\*.json" | ForEach-Object {
    $text = Get-Content $_.FullName -Raw -Encoding UTF8
    $new = $text -replace "change-me-pmo-secret-2026", $secret
    if ($new -ne $text) {
        Set-Content -Path $_.FullName -Value $new -Encoding UTF8 -NoNewline
        Write-Host "Updated $($_.Name)"
    }
}
Write-Host "Token sync complete: $secret"
