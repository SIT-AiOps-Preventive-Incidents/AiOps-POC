#!/usr/bin/env bash
# Undo up.sh and every run: close NIKA sessions (undeploys labs), remove NIKA's images, the model alias and $NIKA_HOME.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/env.sh"
if [ -d "$NIKA_DIR" ]; then
  (cd "$NIKA_DIR" && uv run -q nika session wipe -y) || true
fi
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E '^(nika/|kathara/)' | xargs -r docker rmi -f >/dev/null 2>&1 || true
docker exec "$OLLAMA_CONTAINER" ollama rm "$BENCH_LLM_MODEL" >/dev/null 2>&1 || true
rm -rf "$NIKA_HOME"
echo "removed: NIKA labs, images, model alias $BENCH_LLM_MODEL, $NIKA_HOME (results in $BENCH_DIR/results are kept)"
