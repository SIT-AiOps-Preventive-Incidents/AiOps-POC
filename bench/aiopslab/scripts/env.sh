# Shared settings. Everything the bench creates lives under BENCH_HOME, or in the kind cluster named CLUSTER.
export BENCH_HOME="${BENCH_HOME:-$HOME/aiops-bench}"
export CLUSTER="${CLUSTER:-aiops-bench}"
export AIOPSLAB_CLUSTER="$CLUSTER"                       # AIOpsLab uses kubectl context kind-$AIOPSLAB_CLUSTER
export AIOPSLAB_DIR="$BENCH_HOME/AIOpsLab"
export AIOPSLAB_REF="${AIOPSLAB_REF:-ccf08d0}"            # pinned so results stay comparable
export PATH="$BENCH_HOME/bin:$PATH"
# LLM: the Ollama that the AIOps One stack already runs (container "ollama"), reached on its Docker network address
OLLAMA_CONTAINER="${OLLAMA_CONTAINER:-ollama}"
if [ -z "${BENCH_LLM_URL:-}" ] && command -v docker >/dev/null 2>&1; then
  ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' "$OLLAMA_CONTAINER" 2>/dev/null | awk '{print $1}')
  [ -n "$ip" ] && export BENCH_LLM_URL="http://$ip:11434/v1"
fi
export BENCH_BASE_MODEL="${BENCH_BASE_MODEL:-qwen2.5:1.5b}"
export BENCH_LLM_MODEL="${BENCH_LLM_MODEL:-$BENCH_BASE_MODEL-16k}"   # same model, 16k context: the baseline's prompt needs it
export BENCH_LLM_KEY="${BENCH_LLM_KEY:-none}"
