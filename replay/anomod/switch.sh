#!/usr/bin/env bash
# Switch the demo between the instrumented shop and AnoMod's SocialNetwork replay. Run from anywhere:
#   replay/anomod/switch.sh anomod     # stop the shop, replay SocialNetwork, lab hosts = SocialNetwork services
#   replay/anomod/switch.sh shop       # back to the shop exactly as before
# Incidents, history and settings are kept either way.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
export ANOMOD_DIR="${ANOMOD_DIR:-$HOME/anomod-data}"
SHOP="loadgen frontend-a frontend-b checkout payment inventory edge-fw edge-lb"
MODE="${1:-}"

set_env() {  # DEMO_DATASET=<mode> in the repo's .env, which docker compose reads
  touch "$ROOT/.env"
  grep -v '^DEMO_DATASET=' "$ROOT/.env" > "$ROOT/.env.tmp" || true
  echo "DEMO_DATASET=$1" >> "$ROOT/.env.tmp" && mv "$ROOT/.env.tmp" "$ROOT/.env"
}
lab_up() { [ -d "$ROOT/netlab" ] && DEMO_DATASET="$1" "$ROOT/netlab/up.sh" | tail -2 || true; }

case "$MODE" in
  anomod)
    if [ ! -d "$ANOMOD_DIR/SN_data/trace_data" ]; then
      echo "fetching AnoMod (202 MB) into $ANOMOD_DIR"
      mkdir -p "$ANOMOD_DIR"
      [ -f "$ANOMOD_DIR/AnoMod.zip" ] || curl -fL -o "$ANOMOD_DIR/AnoMod.zip" "https://zenodo.org/records/18342898/files/AnoMod.zip?download=1"
      unzip -q -o "$ANOMOD_DIR/AnoMod.zip" "SN_data/trace_data/*" "SN_data/log_data/*" -d "$ANOMOD_DIR"
    fi
    [ -x "$ROOT/netlab/down.sh" ] && "$ROOT/netlab/down.sh" >/dev/null 2>&1 || true
    (cd "$ROOT" && docker compose stop $SHOP)
    set_env anomod
    (cd "$ROOT" && docker compose up -d aiops-api)
    docker compose -f "$HERE/docker-compose.yml" up -d --build
    lab_up anomod
    echo "demo dataset: AnoMod SocialNetwork (replay status: docker exec anomod-replay python -c \"import urllib.request;print(urllib.request.urlopen('http://localhost:8000/status').read().decode())\")"
    ;;
  shop)
    [ -x "$ROOT/netlab/down.sh" ] && "$ROOT/netlab/down.sh" >/dev/null 2>&1 || true
    docker compose -f "$HERE/docker-compose.yml" down
    set_env shop
    (cd "$ROOT" && docker compose up -d aiops-api $SHOP)
    lab_up shop
    echo "demo dataset: shop"
    ;;
  *) echo "usage: $0 anomod|shop"; exit 2 ;;
esac
