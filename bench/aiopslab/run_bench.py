"""Run agents on AIOpsLab problems and save one JSON per (agent, problem) under results/.

  python run_bench.py --agents aiopsone,baseline --problems problems.txt
Agents:
  aiopsone        this repo's agent (agent/), LLM from BENCH_LLM_URL / BENCH_LLM_MODEL
  aiopsone-rules  the same agent with no LLM at all (shows what the LLM adds)
  baseline        AIOpsLab's own generic OpenAI-compatible agent, on the same model (shell only, the LLM decides everything)
Needs AIOpsLab importable (AIOPSLAB_DIR, set up by scripts/up.sh) and a kind cluster named by AIOPSLAB_CLUSTER.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LAB = os.environ.get("AIOPSLAB_DIR", os.path.expanduser("~/aiops-bench/AIOpsLab"))
sys.path.insert(0, LAB)


def make_agent(name: str):
    from agent import AIOpsOneAgent, NoLLM, OpenAICompatLLM
    if name == "aiopsone":
        return AIOpsOneAgent(OpenAICompatLLM())
    if name == "aiopsone-rules":
        return AIOpsOneAgent(NoLLM())
    if name == "baseline":
        from baseline import make_baseline
        return make_baseline()
    raise SystemExit(f"unknown agent {name}")


def run_one(agent_name: str, pid: str, max_steps: int, out_dir: str) -> dict:
    from aiopslab.orchestrator import Orchestrator
    agent = make_agent(agent_name)
    orch = Orchestrator()
    orch.register_agent(agent, name=agent_name)
    t0 = time.time()
    rec = {"agent": agent_name, "problem": pid, "model": os.environ.get("BENCH_LLM_MODEL")}
    try:
        desc, instr, apis = orch.init_problem(pid)
        agent.init_context(desc, instr, apis)
        asyncio.run(orch.start_problem(max_steps=max_steps))
        rec["results"] = orch.session.results
        rec["steps"] = len(orch.session.history)
    except Exception as e:  # a crashed run is a result too: record it, keep going
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["traceback"] = traceback.format_exc()[-2000:]
    rec["wall_s"] = round(time.time() - t0, 1)
    rec["trace"] = getattr(agent, "trace", None)
    os.makedirs(os.path.join(out_dir, agent_name), exist_ok=True)
    with open(os.path.join(out_dir, agent_name, f"{pid}.json"), "w") as f:
        json.dump(rec, f, indent=1, default=str)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", default="aiopsone,baseline")
    ap.add_argument("--problems", default=os.path.join(HERE, "problems.txt"))
    ap.add_argument("--max-steps", type=int, default=15)
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--skip-done", action="store_true", help="skip pairs that already have a result file")
    a = ap.parse_args()
    pids = [l.split("#")[0].strip() for l in open(a.problems) if l.split("#")[0].strip()]
    for pid in pids:
        for name in a.agents.split(","):
            path = os.path.join(a.out, name, f"{pid}.json")
            if a.skip_done and os.path.exists(path):
                continue
            print(f"\n=== {name} :: {pid}", flush=True)
            rec = run_one(name, pid, a.max_steps, a.out)
            print(f"=== {name} :: {pid} -> {rec.get('results') or rec.get('error')} ({rec['wall_s']} s)", flush=True)


if __name__ == "__main__":
    main()
