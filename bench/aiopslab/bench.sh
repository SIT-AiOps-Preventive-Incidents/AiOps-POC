#!/usr/bin/env bash
# Same targets as the Makefile, for hosts without make:  ./bench.sh up | test | run | report | down
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-}" in
  up) scripts/up.sh ;;
  test) python3 -m pytest -q tests ;;
  run) . scripts/env.sh && "$BENCH_HOME/venv/bin/python" run_bench.py --agents "${AGENTS:-aiopsone,baseline}" --skip-done ;;
  report) python3 report.py ;;
  down) scripts/down.sh ;;
  *) echo "usage: $0 up|test|run|report|down"; exit 2 ;;
esac
