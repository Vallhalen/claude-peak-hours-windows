#!/bin/bash
set -e

HELPER="$HOME/.claude/peak-hours-status.sh"
STATUSLINE="$HOME/.claude/statusline.sh"

MARKER_START="# >>> claude-peak-hours"
MARKER_END="# <<< claude-peak-hours"

echo "Uninstalling Claude Peak Hours status line plugin..."

# Remove helper script
if [ -f "$HELPER" ]; then
    rm "$HELPER"
    echo "Removed peak-hours-status.sh"
fi

# Remove only the injected section from statusline
if [ -f "$STATUSLINE" ] && grep -q "$MARKER_START" "$STATUSLINE"; then
    sed -i.tmp "/$MARKER_START/,/$MARKER_END/d" "$STATUSLINE"
    rm -f "${STATUSLINE}.tmp"
    echo "Removed peak-hours plugin from statusline (rest untouched)"
else
    echo "No peak-hours plugin found in statusline"
fi

echo ""
echo "Done! Your existing status line is preserved. Restart Claude Code to apply."
