#!/bin/bash
# Claude Peak Hours — Status Line for Claude Code
# Shows peak/off-peak status with countdown in the Claude Code terminal status bar.
#
# Install:
#   1. Copy this file to ~/.claude/statusline.sh (or merge with your existing one)
#   2. chmod +x ~/.claude/statusline.sh
#   3. Add to ~/.claude/settings.json:
#      { "statusLine": { "type": "command", "command": "~/.claude/statusline.sh" } }
#
# Requires: jq (brew install jq / apt install jq)

input=$(cat)
model=$(echo "$input" | jq -r '.model.display_name // "Claude"')
percent=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)

# Progress bar
bar_len=20
filled=$(( percent * bar_len / 100 ))
empty=$(( bar_len - filled ))

if [ "$percent" -ge 80 ]; then
  color="\033[38;5;196m"
elif [ "$percent" -ge 50 ]; then
  color="\033[38;5;214m"
else
  color="\033[38;5;78m"
fi
reset="\033[0m"
dim="\033[2m"

bar="${color}"
for ((i=0; i<filled; i++)); do bar+="█"; done
for ((i=0; i<empty; i++)); do bar+="░"; done
bar+="${reset}"

# Peak hours check (weekdays 5-11 AM PT) with countdown
pt_hour=$(TZ=America/Los_Angeles date +%H | sed 's/^0//')
pt_min=$(TZ=America/Los_Angeles date +%M | sed 's/^0//')
pt_dow=$(TZ=America/Los_Angeles date +%w)
pt_seconds=$(( pt_hour * 3600 + pt_min * 60 ))
peak_start=18000   # 5:00 AM = 5*3600
peak_end=39600     # 11:00 AM = 11*3600

is_peak=0
if [ "$pt_dow" -ge 1 ] && [ "$pt_dow" -le 5 ] && [ "$pt_seconds" -ge $peak_start ] && [ "$pt_seconds" -lt $peak_end ]; then
  is_peak=1
fi

# Calculate countdown
if [ "$is_peak" -eq 1 ]; then
  secs_left=$(( peak_end - pt_seconds ))
else
  if [ "$pt_dow" -ge 1 ] && [ "$pt_dow" -le 5 ] && [ "$pt_seconds" -lt $peak_start ]; then
    secs_left=$(( peak_start - pt_seconds ))
  elif [ "$pt_dow" -eq 5 ] && [ "$pt_seconds" -ge $peak_end ]; then
    secs_left=$(( (86400 - pt_seconds) + 2 * 86400 + peak_start ))
  elif [ "$pt_dow" -eq 6 ]; then
    secs_left=$(( (86400 - pt_seconds) + 86400 + peak_start ))
  elif [ "$pt_dow" -eq 0 ]; then
    secs_left=$(( (86400 - pt_seconds) + peak_start ))
  else
    secs_left=$(( (86400 - pt_seconds) + peak_start ))
  fi
fi

# Format countdown
cd_hours=$(( secs_left / 3600 ))
cd_mins=$(( (secs_left % 3600) / 60 ))
if [ "$cd_hours" -gt 24 ]; then
  cd_days=$(( cd_hours / 24 ))
  cd_rh=$(( cd_hours % 24 ))
  countdown="${cd_days}d ${cd_rh}h"
elif [ "$cd_hours" -gt 0 ]; then
  countdown="${cd_hours}h ${cd_mins}m"
else
  countdown="${cd_mins}m"
fi

if [ "$is_peak" -eq 1 ]; then
  peak_color="\033[38;5;196m"
  peak_label="🔴 PEAK ${countdown}"
else
  peak_color="\033[38;5;78m"
  peak_label="🟢 OK ${countdown}"
fi

# Output
printf "${dim}%s${reset}" "$model"
printf " │ ${bar} %d%%" "$percent"
if [ "$percent" -ge 80 ]; then
  blink="\033[5m"
  printf " ${blink}${color}⚠ COMPACT${reset}"
fi
printf " │ ${peak_color}%b${reset}" "$peak_label"
