# Shared settings. Everything this bench creates lives under NIKA_HOME, in Docker containers/images NIKA labels as its
# own (Kathara labs, nika/* images), or in one model alias inside the ollama container.
export NIKA_HOME="${NIKA_HOME:-$HOME/nika-bench}"
export NIKA_DIR="$NIKA_HOME/NIKA"
export NIKA_REF="${NIKA_REF:-dba357b}"                     # pinned so results stay comparable
export PATH="$NIKA_HOME/bin:$PATH"
export UV_CACHE_DIR="$NIKA_HOME/uv-cache"
BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export BENCH_DIR
# LLM for the baseline agent: the Ollama that the AIOps One stack already runs (container "ollama")
OLLAMA_CONTAINER="${OLLAMA_CONTAINER:-ollama}"
if [ -z "${BENCH_LLM_URL:-}" ] && command -v docker >/dev/null 2>&1; then
  ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' "$OLLAMA_CONTAINER" 2>/dev/null | awk '{print $1}')
  [ -n "$ip" ] && export BENCH_LLM_URL="http://$ip:11434/v1"
fi
export BENCH_BASE_MODEL="${BENCH_BASE_MODEL:-qwen2.5:1.5b}"
export BENCH_LLM_MODEL="${BENCH_LLM_MODEL:-$BENCH_BASE_MODEL-nika16k}"   # own alias: independent of other benches
