# Fix certificate trust + reinstall widget
# Run as Administrator

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$msixPath = Join-Path $scriptDir "ClaudePeakWidget.msix"

# 1. Get the cert
$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq "CN=Vallhalen" } | Select-Object -First 1
if (-not $cert) { Write-Host "No certificate found!" -ForegroundColor Red; exit 1 }

Write-Host "Certificate: $($cert.Thumbprint)" -ForegroundColor Cyan

# 2. Add to Trusted Root CA (not just TrustedPeople)
$rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
$rootStore.Open("ReadWrite")
$rootStore.Add($cert)
$rootStore.Close()
Write-Host "Added to Trusted Root CA" -ForegroundColor Green

# 3. Remove old package
Write-Host "Removing old package..." -ForegroundColor Yellow
Get-AppxPackage Vallhalen.ClaudePeakHours | Remove-AppxPackage -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 4. Kill widget host to force re-scan
Stop-Process -Name "Widgets" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "WidgetService" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 5. Reinstall
Write-Host "Installing MSIX..." -ForegroundColor Yellow
Add-AppxPackage -Path $msixPath
Write-Host ""
Write-Host "=== DONE - now try Win+W ===" -ForegroundColor Green
