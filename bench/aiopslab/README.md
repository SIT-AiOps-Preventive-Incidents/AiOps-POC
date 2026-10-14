# AIOpsLab benchmark for the AIOps One agent

Measures the AIOps One way of investigating (read-only evidence playbook → rules → LLM only where unsure → grounding
guard → dry run → act → verify) on [AIOpsLab](https://github.com/microsoft/AIOpsLab) (Microsoft, MLSys 2025), against
AIOpsLab's own baseline agent that lets the LLM drive the shell, **on the same model**.

Nothing here is imported by the AIOps One app, and nothing in the app is imported here. Delete this folder and
the product is unchanged.

```
agent/
  llm.py        model access: any OpenAI-compatible endpoint, or NoLLM (rules only)
  evidence.py   the read-only playbook (kubectl) and parsers -> Findings
  skills.py     rules: anomaly? culprit? fault type? safe fix?
  guard.py      accept an LLM answer only if the evidence supports it
  agent.py      the step loop AIOpsLab drives (get_action), with a full trace of every decision
run_bench.py    run agents × problems -> results/<agent>/<problem>.json
report.py       results -> results/REPORT.md
problems.txt    which problems (13, Hotel Reservation, no Chaos Mesh needed)
scripts/        up.sh / down.sh / env.sh / kind-1node.yaml
tests/          unit tests, no cluster needed
```

## Run

```bash
make test            # unit tests (any machine)
make up              # tools + AIOpsLab into ~/aiops-bench, kind cluster "aiops-bench", model alias with 16k context
make run             # AGENTS=aiopsone,baseline by default; add aiopsone-rules to see what the LLM adds; resumable
make report          # results/REPORT.md
make down            # remove the cluster, the model alias and ~/aiops-bench (results are kept)
```

`make up` needs Docker and network access. It uses the `ollama` container of the AIOps One stack for the LLM; set
`BENCH_LLM_URL` / `BENCH_LLM_MODEL` to use another endpoint or model.

## Fairness rules

- Both agents use the same model and the same context window (16k), at temperature 0.
- The agent's rules are general SRE reasoning about symptoms. They never use knowledge of which service or fault a
  problem injects. Where the benchmark's expected label differs from what the evidence suggests (e.g. a database
  user removed is labelled "Network/Storage Issue"), the agent is not tuned to match.
- In the product a person approves every fix. A benchmark has no person, so approval is automatic here; each trace
  records that, and the mitigation numbers should be read with it in mind.
- The agent only does what AIOps One allows (roll back or restart a workload). Faults that need data or permission
  changes are escalated, and count as failures in the mitigation score.
