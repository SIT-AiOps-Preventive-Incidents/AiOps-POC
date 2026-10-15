#!/usr/bin/env bash
# ./bench.sh up | test | run | report | down
#   run: AGENTS="aiopsone-net byo.langgraph" (default both); results/<agent>/ per agent
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-}" in
  up) scripts/up.sh ;;
  test) python3 -m pytest -q tests ;;
  run)
    . scripts/env.sh
    for a in ${AGENTS:-aiopsone-net byo.langgraph}; do
      m="$BENCH_LLM_MODEL"; [ "$a" = aiopsone-net ] && m=rules
      (cd "$NIKA_DIR" && uv run nika benchmark run --config "$BENCH_DIR/cases.yaml" --result_dir "$BENCH_DIR/results/$a" \
        -a "$a" -p custom -m "$m" --base-url "${BENCH_LLM_URL:-http://localhost:11434/v1}") || echo "run for $a ended with errors"
    done ;;
  report) python3 report.py ;;
  down) scripts/down.sh ;;
  *) echo "usage: $0 up|test|run|report|down"; exit 2 ;;
esac
