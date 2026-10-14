#!/usr/bin/env bash
# Install NIKA into $NIKA_HOME and register this agent with it. Safe to re-run.
# Needs Docker. Touches nothing outside $NIKA_HOME except: Docker images/containers NIKA builds for its labs, and one
# model alias in the ollama container. No apt, no sudo: dc_clos runs on Kathara, which needs neither vrf nor Containerlab.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/env.sh"
command -v docker >/dev/null || { echo "docker is required"; exit 1; }
mkdir -p "$NIKA_HOME/bin"
if [ ! -x "$NIKA_HOME/bin/uv" ]; then
  curl -fsSL https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$NIKA_HOME/bin" INSTALLER_NO_MODIFY_PATH=1 sh
fi
if [ ! -d "$NIKA_DIR/.git" ]; then
  git clone -q https://github.com/sands-lab/nika.git "$NIKA_DIR"
fi
git -C "$NIKA_DIR" checkout -q "$NIKA_REF"
cd "$NIKA_DIR"
uv sync -q --python 3.12
[ -f .env ] || : > .env
mkdir -p config
cat > config/nika.yaml <<CFG
# Written by AiOps-POC bench/nika/scripts/up.sh
agent:
  type: byo.langgraph
  provider: custom
  model: $BENCH_LLM_MODEL
  base_url: ${BENCH_LLM_URL:-http://localhost:11434/v1}
  max_steps: 20
  timeout_sec: 1500
  enable_skills: false
  max_tokens: 1024
nika:
  result_dir: results
  observability:
    langfuse_enabled: false
  lab:
    deploy_attempts: 3
benchmark:
  case_timeout_sec: 2000
CFG
uv run -q nika agent add "$BENCH_DIR"
if [ -n "${BENCH_LLM_URL:-}" ] && ! docker exec "$OLLAMA_CONTAINER" ollama list 2>/dev/null | grep -q "^$BENCH_LLM_MODEL"; then
  printf 'FROM %s\nPARAMETER num_ctx 16384\n' "$BENCH_BASE_MODEL" | docker exec -i "$OLLAMA_CONTAINER" sh -c "cat > /tmp/Modelfile.nika && ollama create $BENCH_LLM_MODEL -f /tmp/Modelfile.nika"
fi
echo "ready: NIKA $NIKA_REF in $NIKA_DIR, agent aiopsone-net registered, baseline LLM $BENCH_LLM_MODEL at ${BENCH_LLM_URL:-<unset>}"
