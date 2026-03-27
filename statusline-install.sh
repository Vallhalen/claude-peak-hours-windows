#!/bin/bash
set -e

HELPER_URL="https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/peak-hours-status.sh"
HELPER="$HOME/.claude/peak-hours-status.sh"
STATUSLINE="$HOME/.claude/statusline.sh"
SETTINGS="$HOME/.claude/settings.json"

MARKER_START="# >>> claude-peak-hours"
MARKER_END="# <<< claude-peak-hours"

echo "Installing Claude Peak Hours status line plugin..."

# Create .claude dir if needed
mkdir -p "$HOME/.claude"

# Download helper script
curl -sL "$HELPER_URL" -o "$HELPER"
chmod +x "$HELPER"
echo "Downloaded peak-hours-status.sh"

# Check if statusline.sh exists
if [ -f "$STATUSLINE" ]; then
    # Remove old peak-hours injection if present
    if grep -q "$MARKER_START" "$STATUSLINE"; then
        sed -i.tmp "/$MARKER_START/,/$MARKER_END/d" "$STATUSLINE"
        rm -f "${STATUSLINE}.tmp"
        echo "Removed previous peak-hours plugin"
    fi

    # Append peak-hours segment to existing statusline
    cat >> "$STATUSLINE" << 'INJECT'
# >>> claude-peak-hours
printf " │ "; ~/.claude/peak-hours-status.sh
# <<< claude-peak-hours
INJECT
    echo "Added peak-hours plugin to existing statusline"

else
    # No statusline exists — create minimal one
    cat > "$STATUSLINE" << 'SCRIPT'
#!/bin/bash
input=$(cat)
model=$(echo "$input" | jq -r '.model.display_name // "Claude"' 2>/dev/null)
printf "%s" "${model:-Claude}"
# >>> claude-peak-hours
printf " │ "; ~/.claude/peak-hours-status.sh
# <<< claude-peak-hours
SCRIPT
    chmod +x "$STATUSLINE"
    echo "Created statusline with peak-hours plugin"

    # Configure settings.json if needed
    if [ -f "$SETTINGS" ]; then
        if ! grep -q "statusLine" "$SETTINGS"; then
            tmp=$(mktemp)
            jq '. + {"statusLine": {"type": "command", "command": "~/.claude/statusline.sh"}}' "$SETTINGS" > "$tmp"
            mv "$tmp" "$SETTINGS"
            echo "Added statusLine config to settings.json"
        fi
    else
        echo '{"statusLine": {"type": "command", "command": "~/.claude/statusline.sh"}}' > "$SETTINGS"
        echo "Created settings.json with statusLine config"
    fi
fi

echo ""
echo "Done! Restart Claude Code to see peak hours in your status line."
echo "Uninstall: curl -sL https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/statusline-uninstall.sh | bash"
