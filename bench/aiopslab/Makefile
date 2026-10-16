# AIOpsLab benchmark for the AIOps One agent. Self-contained: `make down` removes everything `make up` added.
SHELL := /bin/bash
ENV := . scripts/env.sh &&
PY := $$BENCH_HOME/venv/bin/python
AGENTS ?= aiopsone,baseline

.PHONY: up test run report down
up:      ## install tools + AIOpsLab into ~/aiops-bench, create kind cluster "aiops-bench"
	scripts/up.sh
test:    ## unit tests (no cluster, no LLM)
	python3 -m pytest -q tests
run:     ## run AGENTS on problems.txt; resumable
	$(ENV) $(PY) run_bench.py --agents $(AGENTS) --skip-done
report:  ## results/REPORT.md
	python3 report.py
down:    ## delete the cluster, the model alias and ~/aiops-bench (results kept)
	scripts/down.sh
