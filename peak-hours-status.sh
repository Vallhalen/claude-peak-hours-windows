#!/bin/bash
# Claude Peak Hours — standalone segment
# Outputs: 🟢 OK 6h 34m  or  🔴 PEAK 2h 15m
# Call from your statusline: printf " │ "; ~/.claude/peak-hours-status.sh

pt_hour=$(TZ=America/Los_Angeles date +%H | sed 's/^0//')
pt_min=$(TZ=America/Los_Angeles date +%M | sed 's/^0//')
pt_dow=$(TZ=America/Los_Angeles date +%w)
pt_seconds=$(( pt_hour * 3600 + pt_min * 60 ))
peak_start=18000
peak_end=39600

is_peak=0
if [ "$pt_dow" -ge 1 ] && [ "$pt_dow" -le 5 ] && [ "$pt_seconds" -ge $peak_start ] && [ "$pt_seconds" -lt $peak_end ]; then
  is_peak=1
fi

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

cd_hours=$(( secs_left / 3600 ))
cd_mins=$(( (secs_left % 3600) / 60 ))
if [ "$cd_hours" -gt 24 ]; then
  countdown="$(( cd_hours / 24 ))d $(( cd_hours % 24 ))h"
elif [ "$cd_hours" -gt 0 ]; then
  countdown="${cd_hours}h ${cd_mins}m"
else
  countdown="${cd_mins}m"
fi

if [ "$is_peak" -eq 1 ]; then
  printf "\033[38;5;196m🔴 PEAK %s\033[0m" "$countdown"
else
  printf "\033[38;5;78m🟢 OK %s\033[0m" "$countdown"
fi
