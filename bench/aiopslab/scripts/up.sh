#!/usr/bin/env bash
# Install everything the benchmark needs into $BENCH_HOME and create the kind cluster. Safe to re-run.
# Touches nothing outside $BENCH_HOME except: the kind cluster "$CLUSTER", and one model alias in the ollama container.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/env.sh"
mkdir -p "$BENCH_HOME/bin"
arch=$(uname -m); [ "$arch" = x86_64 ] && arch=amd64; [ "$arch" = aarch64 ] && arch=arm64
os=$(uname -s | tr '[:upper:]' '[:lower:]')

fetch() { [ -x "$BENCH_HOME/bin/$1" ] || { echo "installing $1"; curl -fsSL -o "$BENCH_HOME/bin/$1" "$2"; chmod +x "$BENCH_HOME/bin/$1"; }; }
fetch kind    "https://kind.sigs.k8s.io/dl/v0.27.0/kind-$os-$arch"
fetch kubectl "https://dl.k8s.io/release/v1.32.3/bin/$os/$arch/kubectl"
if [ ! -x "$BENCH_HOME/bin/helm" ]; then
  curl -fsSL "https://get.helm.sh/helm-v3.17.2-$os-$arch.tar.gz" | tar -xz -C "$BENCH_HOME/bin" --strip-components=1 "$os-$arch/helm"
fi
if [ ! -x "$BENCH_HOME/bin/uv" ]; then
  curl -fsSL https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$BENCH_HOME/bin" INSTALLER_NO_MODIFY_PATH=1 sh
fi

if [ ! -d "$AIOPSLAB_DIR/.git" ]; then
  git clone -q https://github.com/microsoft/AIOpsLab.git "$AIOPSLAB_DIR"
fi
git -C "$AIOPSLAB_DIR" checkout -q "$AIOPSLAB_REF"
git -C "$AIOPSLAB_DIR" submodule update -q --init --recursive
cat > "$AIOPSLAB_DIR/aiopslab/config.yml" <<CFG
k8s_host: kind
k8s_user: $(whoami)
ssh_key_path: ~/.ssh/id_rsa
data_dir: data
qualitative_eval: false
print_session: false
CFG

if [ ! -x "$BENCH_HOME/venv/bin/python" ]; then
  "$BENCH_HOME/bin/uv" venv -q --python 3.12 "$BENCH_HOME/venv"
fi
VIRTUAL_ENV="$BENCH_HOME/venv" "$BENCH_HOME/bin/uv" pip install -q -e "$AIOPSLAB_DIR" pytest

if ! kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  kind create cluster --name "$CLUSTER" --config "$HERE/kind-1node.yaml"
fi

if [ -n "${BENCH_LLM_URL:-}" ] && ! docker exec "$OLLAMA_CONTAINER" ollama list 2>/dev/null | grep -q "^$BENCH_LLM_MODEL"; then
  printf 'FROM %s\nPARAMETER num_ctx 16384\n' "$BENCH_BASE_MODEL" | docker exec -i "$OLLAMA_CONTAINER" sh -c "cat > /tmp/Modelfile.bench && ollama create $BENCH_LLM_MODEL -f /tmp/Modelfile.bench"
fi
echo "ready: cluster kind-$CLUSTER, LLM $BENCH_LLM_MODEL at ${BENCH_LLM_URL:-<set BENCH_LLM_URL>}"
