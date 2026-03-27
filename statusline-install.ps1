# Claude Peak Hours — Status Line Installer (PowerShell/Windows)

$claudeDir = Join-Path $env:USERPROFILE ".claude"
$helper = Join-Path $claudeDir "peak-hours-status.ps1"
$statusline = Join-Path $claudeDir "statusline.ps1"
$settings = Join-Path $claudeDir "settings.json"
$helperUrl = "https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/peak-hours-status.ps1"

$markerStart = "# >>> claude-peak-hours"
$markerEnd = "# <<< claude-peak-hours"

Write-Host "Installing Claude Peak Hours status line plugin..."

# Create .claude dir if needed
if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir | Out-Null }

# Download helper
Invoke-WebRequest -Uri $helperUrl -OutFile $helper
Write-Host "Downloaded peak-hours-status.ps1"

# Inject into existing statusline or create new one
if (Test-Path $statusline) {
    $content = Get-Content $statusline -Raw

    # Remove old injection
    if ($content -match [regex]::Escape($markerStart)) {
        $content = $content -replace "(?s)$([regex]::Escape($markerStart)).*?$([regex]::Escape($markerEnd))\r?\n?", ""
    }

    # Append
    $inject = @"

$markerStart
Write-Host -NoNewline " | "; & `$PSScriptRoot/peak-hours-status.ps1
$markerEnd
"@
    $content + $inject | Set-Content $statusline
    Write-Host "Added peak-hours plugin to existing statusline"
} else {
    # Create minimal statusline
    @"
`$input = `$input | ConvertFrom-Json -ErrorAction SilentlyContinue
`$model = if (`$input.model.display_name) { `$input.model.display_name } else { "Claude" }
Write-Host -NoNewline `$model
$markerStart
Write-Host -NoNewline " | "; & "`$PSScriptRoot/peak-hours-status.ps1"
$markerEnd
"@ | Set-Content $statusline
    Write-Host "Created statusline with peak-hours plugin"
}

# Configure settings.json
if (Test-Path $settings) {
    $json = Get-Content $settings -Raw | ConvertFrom-Json
    if (-not $json.statusLine) {
        $json | Add-Member -NotePropertyName "statusLine" -NotePropertyValue @{
            type = "command"
            command = "powershell -File ~/.claude/statusline.ps1"
        }
        $json | ConvertTo-Json -Depth 10 | Set-Content $settings
        Write-Host "Added statusLine config to settings.json"
    }
} else {
    @{ statusLine = @{ type = "command"; command = "powershell -File ~/.claude/statusline.ps1" } } |
        ConvertTo-Json -Depth 10 | Set-Content $settings
    Write-Host "Created settings.json with statusLine config"
}

Write-Host ""
Write-Host "Done! Restart Claude Code to see peak hours in your status line."
