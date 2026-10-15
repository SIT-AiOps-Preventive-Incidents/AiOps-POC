#!/usr/bin/env bash
# Start or stop the NIKA bridge (bridge.py) on this host. It runs inside NIKA's virtualenv (it needs PyYAML and the
# NIKA CLI) and listens on the "aiops" Docker network's gateway only, so aiops-api can reach it and nothing outside can.
#   bench/nika/bridge.sh start|stop|status
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/scripts/env.sh"
PIDF="$NIKA_HOME/bridge.pid"
GW=$(docker network inspect -f '{{range .IPAM.Config}}{{.Gateway}}{{end}}' aiops)
case "${1:-}" in
  start)
    [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null && { echo "already running"; exit 0; }
    python3 "$HERE/scripts/patch_kathara_noipv6.py" "$(ls -d "$NIKA_DIR"/.venv/lib/python3*/site-packages/Kathara/manager/docker/DockerMachine.py)"
    BRIDGE_HOST="$GW" NIKA_DIR="$NIKA_DIR" nohup "$NIKA_DIR/.venv/bin/python" "$HERE/bridge.py" > "$NIKA_HOME/bridge.log" 2>&1 &
    echo $! > "$PIDF"; sleep 1; echo "bridge on http://$GW:18900 (log $NIKA_HOME/bridge.log)" ;;
  stop) [ -f "$PIDF" ] && kill "$(cat "$PIDF")" 2>/dev/null; rm -f "$PIDF"; echo stopped ;;
  status) curl -s "http://$GW:18900/status"; echo ;;
  *) echo "usage: $0 start|stop|status"; exit 2 ;;
esac
