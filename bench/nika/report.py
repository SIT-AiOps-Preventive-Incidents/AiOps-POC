"""Summarise results/<agent>/ into a markdown table (stdout and results/REPORT.md). Reads NIKA's own per-trial files
(eval_metrics.json and the ground truth / submission beside it); no lab needed."""
from __future__ import annotations

import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
COLS = [("detection_score", "detect"), ("localization_f1", "where"), ("fault_type_f1", "what"), ("rca_f1", "both")]


def load(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def problem_of(trial_dir: str) -> str:
    for name in ("ground_truth.json", "run.json", "session.json"):
        d = load(os.path.join(trial_dir, name))
        for key in ("problem", "problem_names", "root_cause_name"):
            v = d.get(key)
            if v:
                return "+".join(v) if isinstance(v, list) else str(v)
        if name == "ground_truth.json" and d.get("is_anomaly") is False:
            return "healthy"
    return os.path.basename(trial_dir)


def trials(out_dir: str) -> list[dict]:
    rows = []
    for agent_dir in sorted(glob.glob(os.path.join(out_dir, "*"))):
        if not os.path.isdir(agent_dir):
            continue
        for m in sorted(glob.glob(os.path.join(agent_dir, "**", "eval_metrics.json"), recursive=True)):
            d = os.path.dirname(m)
            metrics = load(m)
            rows.append({"agent": os.path.basename(agent_dir), "problem": problem_of(d), "metrics": metrics,
                         "submission": load(os.path.join(d, "submission.json")), "dir": d})
    return rows


def fmt(v) -> str:
    return "-" if v is None else f"{float(v):.2f}"


def main(out_dir: str = os.path.join(HERE, "results")) -> str:
    rows = trials(out_dir)
    agents = sorted({r["agent"] for r in rows})
    problems = sorted({r["problem"] for r in rows}, key=lambda p: (p != "healthy", p))
    cell = {(r["agent"], r["problem"]): r for r in rows}
    head = "| Fault | " + " | ".join(f"{a} (detect / where / what)" for a in agents) + " |"
    lines = [head, "|---|" + "---|" * len(agents)]
    for p in problems:
        vals = []
        for a in agents:
            r = cell.get((a, p))
            m = r["metrics"] if r else {}
            vals.append(" / ".join(fmt(m.get(k)) for k, _ in COLS[:3]) if r else "not run")
        lines.append(f"| {p} | " + " | ".join(vals) + " |")
    lines += ["", "| Agent | trials | " + " | ".join(label for _, label in COLS) + " |", "|---|---|" + "---|" * len(COLS)]
    for a in agents:
        ms = [r["metrics"] for r in rows if r["agent"] == a]
        means = [sum(float(m.get(k) or 0) for m in ms) / len(ms) if ms else 0 for k, _ in COLS]
        lines.append(f"| {a} | {len(ms)} | " + " | ".join(f"{v:.2f}" for v in means) + " |")
    text = "\n".join(lines)
    with open(os.path.join(out_dir, "REPORT.md"), "w") as f:
        f.write("# NIKA results (dc_clos, small)\n\nScores are NIKA's own (eval_metrics.json): detect = is_anomaly right, "
                "where = localization F1, what = fault-type F1, both = joint root-cause F1. A trial with no submission "
                "scores 0.\n\n" + text + "\n")
    print(text)
    return text


if __name__ == "__main__":
    main()
