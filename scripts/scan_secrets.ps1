# Pre-push secret scan (local / CI helper)
# Fails if likely secrets are found in tracked paths.
param(
    [string]$Root = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

$ErrorActionPreference = "Stop"
Set-Location $Root

$patterns = @(
    @{ Name = "OpenAI key"; Regex = 'sk-[a-zA-Z0-9]{20,}' },
    @{ Name = "GitHub token"; Regex = 'ghp_[a-zA-Z0-9]{20,}' },
    @{ Name = "AWS key"; Regex = 'AKIA[0-9A-Z]{16}' },
    @{ Name = "Private key block"; Regex = '-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----' }
)

$tracked = @(git -C $Root ls-files | ForEach-Object { $_.Trim().Trim('"') } | Where-Object { $_ })

$hits = @()
foreach ($file in $tracked) {
    if ($file -match '(^|/)node_modules/') { continue }
    if ($file -match '\.(png|gif|jpg|jpeg|ico|pdf|docx|tar|gz|zip)$') { continue }
    $full = Join-Path $Root $file
    if (-not (Test-Path -LiteralPath $full)) { continue }
    $text = Get-Content -LiteralPath $full -Raw -ErrorAction SilentlyContinue
    if (-not $text) { continue }
    foreach ($p in $patterns) {
        if ($text -match $p.Regex) {
            $hits += [pscustomobject]@{ File = $file; Pattern = $p.Name }
        }
    }
}

if ($tracked -contains '.env') {
    $hits += [pscustomobject]@{ File = '.env'; Pattern = 'tracked .env file' }
}

if ($hits.Count -gt 0) {
    Write-Host "SECRET SCAN FAILED:" -ForegroundColor Red
    $hits | Format-Table -AutoSize
    exit 1
}

Write-Host "Secret scan PASS ($($tracked.Count) tracked files)" -ForegroundColor Green
