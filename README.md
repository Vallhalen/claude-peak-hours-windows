# Claude Peak Hours

Know when to go all out and when to conserve tokens. Two tools — pick what fits your workflow:

1. **macOS Menu Bar App** — always-visible indicator with popover details
2. **Claude Code Status Line** — peak/off-peak status right in your terminal (cross-platform)

During peak hours (weekdays 5 AM – 11 AM PT), Anthropic applies stricter session limits. These tools give you a clear indicator so you never get surprised by throttling.

## Features

### macOS Menu Bar App
- **Menu bar indicator** — green circle + "Full power" or red circle + "Restricted"
- **Warning mode** — orange indicator 15 minutes before a status change
- **Popover details** — click for countdown timer, restriction hours in your local timezone
- **Notifications** — optional macOS alerts when peak hours start/end
- **Launch at login** — optional auto-start
- **Localized** — Polish and English, auto-detected from system language
- **Lightweight** — native Swift + SwiftUI, ~46 MB RAM, no dependencies

### Claude Code Status Line
- **Terminal status bar** — 🟢 OK 6h 34m / 🔴 PEAK 2h 15m
- **Countdown** — time until next status change
- **Context bar** — shows context window usage with color coding
- **Cross-platform** — works on macOS, Linux, Windows (WSL/Git Bash)
- **Requires** — `jq` and Claude Code

## Requirements

### Menu Bar App
- macOS 13 (Ventura) or later
- Xcode Command Line Tools (`xcode-select --install`)

### Status Line
- Claude Code CLI
- `jq` (`brew install jq` / `apt install jq`)

## Install

### One-liner (recommended)

```bash
curl -sL https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/install.sh | bash
```

Downloads the latest release, installs to `/Applications`, and starts the app.

### Download manually

1. Go to [Releases](https://github.com/studiogo/claude-peak-hours/releases)
2. Download `Claude-Peak-Hours-v*.zip`
3. Unzip and move `Claude Peak Hours.app` to `/Applications`

### Build from source

```bash
git clone https://github.com/studiogo/claude-peak-hours.git
cd claude-peak-hours
./build.sh
cp -r "build/Claude Peak Hours.app" /Applications/
```

## Peak Hours Schedule

Based on [Anthropic's announcement](https://www.anthropic.com):

| | Peak | Off-Peak |
|---|---|---|
| **When** | Weekdays 5:00–11:00 AM PT | Evenings, nights, weekends |
| **PT** | 5:00–11:00 | All other times |
| **CET** | 14:00–20:00 | All other times |
| **Effect** | Faster session limit usage | Normal session limits |

The app auto-converts to your local timezone.

## Install Claude Code Status Line

```bash
# 1. Download the script
curl -sL https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/claude-code-statusline.sh -o ~/.claude/statusline.sh
chmod +x ~/.claude/statusline.sh

# 2. Add to Claude Code settings (~/.claude/settings.json)
# If you don't have settings.json yet:
echo '{ "statusLine": { "type": "command", "command": "~/.claude/statusline.sh" } }' > ~/.claude/settings.json

# If you already have settings.json, add the statusLine key manually
```

Or merge with your existing status line script — the peak hours section is clearly marked in the file.

## How It Works

No API calls, no network requests. Both tools simply check the current time against the known peak hours schedule (weekdays 5–11 AM Pacific Time).

- **Menu bar app** — updates every 30 seconds
- **Status line** — updates after each Claude Code response

## License

MIT
