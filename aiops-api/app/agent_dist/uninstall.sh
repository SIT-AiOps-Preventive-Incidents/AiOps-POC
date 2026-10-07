#!/bin/sh
# Remove the AIOps host agent from this machine.
DIR="$HOME/.aiops-agent"
PL="$HOME/Library/LaunchAgents/com.aiops.agent.plist"
if [ -f "$PL" ]; then launchctl unload "$PL" 2>/dev/null; rm -f "$PL"; fi
pkill -f "$DIR/aiops-agent.py" 2>/dev/null || true
( crontab -l 2>/dev/null | grep -v aiops-agent.py ) | crontab - 2>/dev/null || true
rm -rf "$DIR"
echo "AIOps agent removed. Remove the host in the web app (Infrastructure) if you no longer need its history."
