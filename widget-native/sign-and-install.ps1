# Sign and install Claude Peak Hours widget MSIX
# Must be run as Administrator

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$msixPath = Join-Path $scriptDir "ClaudePeakWidget.msix"

Write-Host "=== Claude Peak Hours Widget - Install ===" -ForegroundColor Cyan

# 1. Create self-signed certificate (if not exists)
$certSubject = "CN=Vallhalen"
$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $certSubject -and $_.NotAfter -gt (Get-Date) } | Select-Object -First 1

if (-not $cert) {
    Write-Host "Creating self-signed certificate..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate `
        -Type Custom `
        -Subject $certSubject `
        -KeyUsage DigitalSignature `
        -FriendlyName "Claude Peak Hours Dev" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
    Write-Host "Certificate created: $($cert.Thumbprint)" -ForegroundColor Green
} else {
    Write-Host "Using existing certificate: $($cert.Thumbprint)" -ForegroundColor Green
}

# 2. Trust the certificate (add to Trusted Root)
$rootStore = Get-ChildItem Cert:\LocalMachine\TrustedPeople | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
if (-not $rootStore) {
    Write-Host "Adding certificate to Trusted People store (needs Admin)..." -ForegroundColor Yellow
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPeople", "LocalMachine")
    $store.Open("ReadWrite")
    $store.Add($cert)
    $store.Close()
    Write-Host "Certificate trusted." -ForegroundColor Green
}

# 3. Sign the MSIX
$signtool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" -Recurse | Select-Object -Last 1
if (-not $signtool) {
    Write-Host "ERROR: signtool.exe not found. Install Windows SDK." -ForegroundColor Red
    exit 1
}

Write-Host "Signing MSIX..." -ForegroundColor Yellow
& $signtool.FullName sign /fd SHA256 /sha1 $cert.Thumbprint /t http://timestamp.digicert.com $msixPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Signing failed." -ForegroundColor Red
    exit 1
}
Write-Host "MSIX signed." -ForegroundColor Green

# 4. Install the package
Write-Host "Installing MSIX package..." -ForegroundColor Yellow
Add-AppxPackage -Path $msixPath
Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Green
Write-Host "Now open Widgets panel (Win+W) > click '+' > find 'Claude Peak Hours'" -ForegroundColor Cyan
