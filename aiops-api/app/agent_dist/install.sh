#!/bin/sh
# AIOps host agent installer (macOS / Linux). No sudo, no inbound ports.
#   curl -fsSL __API__/install/agent.sh | AIOPS_HOST_NAME=my-laptop sh
set -e
API="__API__"
OTLP="__OTLP__"
NAME="${AIOPS_HOST_NAME:-$(hostname -s 2>/dev/null || hostname)}"
NAME=$(printf '%s' "$NAME" | tr 'A-Z ' 'a-z-' | tr -cd 'a-z0-9._-')
DIR="$HOME/.aiops-agent"
PY=$(command -v python3 || true)

say() { printf '  %s\n' "$1"; }
echo "AIOps agent -> $API"
[ -n "$PY" ] || { say "python3 not found. Install it first (macOS: xcode-select --install)."; exit 1; }
curl -fsS -m 5 "$API/api/v1/health" -o /dev/null || curl -fsS -m 5 "$API/api/ping" >/dev/null || { say "Cannot reach $API - are you on the campus network / VPN?"; exit 1; }

mkdir -p "$DIR"
curl -fsSL "$API/install/aiops-agent.py" -o "$DIR/aiops-agent.py"
printf '{"host":"%s","otlp":"%s","api":"%s"}\n' "$NAME" "$OTLP" "$API" > "$DIR/config.json"
say "installed to $DIR"

OS=$(uname -s)
curl -fsS -X PUT "$API/api/v1/hosts/$NAME" -H 'Content-Type: application/json' \
  -d "{\"os\":\"$(uname -sr)\",\"arch\":\"$(uname -m)\",\"kind\":\"$( [ "$OS" = Darwin ] && echo workstation || echo server )\"}" >/dev/null
say "registered as '$NAME'"

if [ "$OS" = Darwin ]; then
  PL="$HOME/Library/LaunchAgents/com.aiops.agent.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PL" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.aiops.agent</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$DIR/aiops-agent.py</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$DIR/agent.log</string>
  <key>StandardErrorPath</key><string>$DIR/agent.log</string>
</dict></plist>
EOF
  launchctl unload "$PL" 2>/dev/null || true
  launchctl load -w "$PL"
  say "running as LaunchAgent com.aiops.agent (starts at login)"
else
  pkill -f "$DIR/aiops-agent.py" 2>/dev/null || true
  nohup "$PY" "$DIR/aiops-agent.py" >> "$DIR/agent.log" 2>&1 &
  ( crontab -l 2>/dev/null | grep -v aiops-agent.py; echo "@reboot $PY $DIR/aiops-agent.py >> $DIR/agent.log 2>&1" ) | crontab - 2>/dev/null || true
  say "running in background (restarts on reboot via crontab)"
fi
echo "Done. '$NAME' shows up in AIOps within ~30 seconds."
echo "Remove later with: curl -fsSL $API/install/uninstall.sh | sh"
