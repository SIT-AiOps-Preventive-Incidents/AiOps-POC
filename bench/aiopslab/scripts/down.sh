#!/usr/bin/env bash
# Remove everything up.sh created. Results in ./results are kept unless PURGE_RESULTS=1.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/env.sh"
command -v kind >/dev/null && kind delete cluster --name "$CLUSTER" 2>/dev/null
docker exec "$OLLAMA_CONTAINER" ollama rm "$BENCH_LLM_MODEL" >/dev/null 2>&1 && echo "removed model alias $BENCH_LLM_MODEL"
rm -rf "$BENCH_HOME"
[ "${PURGE_RESULTS:-0}" = 1 ] && rm -rf "$HERE/../results"
echo "removed: kind cluster $CLUSTER and $BENCH_HOME"
