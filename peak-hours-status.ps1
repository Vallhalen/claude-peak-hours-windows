# Claude Peak Hours — standalone segment (PowerShell)
# Outputs: 🟢 OK 6h 34m  or  🔴 PEAK 2h 15m

$pt = [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId((Get-Date), "America/Los_Angeles")
$ptHour = $pt.Hour
$ptDow = [int]$pt.DayOfWeek  # 0=Sun, 1-5=Mon-Fri, 6=Sat
$ptSeconds = $ptHour * 3600 + $pt.Minute * 60
$peakStart = 18000  # 5:00 AM
$peakEnd = 39600    # 11:00 AM

$isPeak = ($ptDow -ge 1 -and $ptDow -le 5 -and $ptSeconds -ge $peakStart -and $ptSeconds -lt $peakEnd)

if ($isPeak) {
    $secsLeft = $peakEnd - $ptSeconds
} else {
    if ($ptDow -ge 1 -and $ptDow -le 5 -and $ptSeconds -lt $peakStart) {
        $secsLeft = $peakStart - $ptSeconds
    } elseif ($ptDow -eq 5 -and $ptSeconds -ge $peakEnd) {
        $secsLeft = (86400 - $ptSeconds) + 2 * 86400 + $peakStart
    } elseif ($ptDow -eq 6) {
        $secsLeft = (86400 - $ptSeconds) + 86400 + $peakStart
    } elseif ($ptDow -eq 0) {
        $secsLeft = (86400 - $ptSeconds) + $peakStart
    } else {
        $secsLeft = (86400 - $ptSeconds) + $peakStart
    }
}

$cdHours = [math]::Floor($secsLeft / 3600)
$cdMins = [math]::Floor(($secsLeft % 3600) / 60)

if ($cdHours -gt 24) {
    $countdown = "$([math]::Floor($cdHours / 24))d $($cdHours % 24)h"
} elseif ($cdHours -gt 0) {
    $countdown = "${cdHours}h ${cdMins}m"
} else {
    $countdown = "${cdMins}m"
}

$esc = [char]27
if ($isPeak) {
    Write-Host -NoNewline "${esc}[38;5;196m🔴 PEAK ${countdown}${esc}[0m"
} else {
    Write-Host -NoNewline "${esc}[38;5;78m🟢 OK ${countdown}${esc}[0m"
}
