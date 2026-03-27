# Claude Peak Hours — Status Line Uninstaller (PowerShell/Windows)

$claudeDir = Join-Path $env:USERPROFILE ".claude"
$helper = Join-Path $claudeDir "peak-hours-status.ps1"
$statusline = Join-Path $claudeDir "statusline.ps1"

$markerStart = "# >>> claude-peak-hours"
$markerEnd = "# <<< claude-peak-hours"

Write-Host "Uninstalling Claude Peak Hours status line plugin..."

# Remove helper
if (Test-Path $helper) {
    Remove-Item $helper
    Write-Host "Removed peak-hours-status.ps1"
}

# Remove injected section from statusline
if (Test-Path $statusline) {
    $content = Get-Content $statusline -Raw
    if ($content -match [regex]::Escape($markerStart)) {
        $content = $content -replace "(?s)\r?\n?$([regex]::Escape($markerStart)).*?$([regex]::Escape($markerEnd))", ""
        $content | Set-Content $statusline
        Write-Host "Removed peak-hours plugin from statusline (rest untouched)"
    } else {
        Write-Host "No peak-hours plugin found in statusline"
    }
} else {
    Write-Host "No statusline found"
}

Write-Host ""
Write-Host "Done! Your existing status line is preserved. Restart Claude Code to apply."
