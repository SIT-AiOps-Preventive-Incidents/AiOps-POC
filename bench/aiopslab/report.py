"""Summarise results/ into a markdown table (stdout and results/REPORT.md). Reads only the JSON files; no cluster needed."""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = ["detection", "localization", "analysis", "mitigation"]


def task_of(pid: str) -> str:
    return next((t for t in TASKS if f"-{t}-" in pid or f"_{t}_" in pid or pid.startswith(f"noop_{t}")), "other")


def outcome(rec: dict) -> str:
    if rec.get("error"):
        return "error"
    if any(t.get("kind") == "analysis" and t.get("evidence_ok") is False for t in rec.get("trace") or []):
        return "no-evidence"   # the agent could not see the cluster; never counted as a pass
    r = rec.get("results") or {}
    if "success" in r:
        return "pass" if r["success"] else "fail"
    if "Detection Accuracy" in r:
        return "pass" if r["Detection Accuracy"] == "Correct" else "fail"
    if "Localization Accuracy" in r:
        return "pass" if (r.get("Localization Accuracy") or 0) >= 100 else "fail"
    return "fail"


def main(out_dir: str = os.path.join(HERE, "results")) -> str:
    recs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(out_dir, "*", "*.json")))]
    agents = sorted({r["agent"] for r in recs})
    problems = sorted({r["problem"] for r in recs})
    cell = {(r["agent"], r["problem"]): r for r in recs}
    lines = ["| Problem | " + " | ".join(agents) + " |", "|---|" + "---|" * len(agents)]
    score = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for p in problems:
        row = []
        for a in agents:
            r = cell.get((a, p))
            if not r:
                row.append("-")
                continue
            o = outcome(r)
            s = score[a][task_of(p)]
            s[0] += o == "pass"
            s[1] += 1
            row.append(f"{o} ({r.get('wall_s', 0):.0f} s)")
        lines.append(f"| {p} | " + " | ".join(row) + " |")
    lines += ["", "| Agent | " + " | ".join(TASKS) + " | total |", "|---|" + "---|" * (len(TASKS) + 1)]
    for a in agents:
        tot = [sum(score[a][t][i] for t in TASKS) for i in (0, 1)]
        lines.append(f"| {a} | " + " | ".join(f"{score[a][t][0]}/{score[a][t][1]}" for t in TASKS) + f" | {tot[0]}/{tot[1]} |")
    text = "\n".join(lines)
    with open(os.path.join(out_dir, "REPORT.md"), "w") as f:
        f.write(f"# AIOpsLab results\n\nModel: {recs[0].get('model') if recs else '-'}\n\n{text}\n")
    print(text)
    return text


if __name__ == "__main__":
    main()
