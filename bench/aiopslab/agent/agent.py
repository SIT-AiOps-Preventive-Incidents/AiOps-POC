"""AIOps One-style agent for AIOpsLab: the orchestrator that ties the parts together.

  evidence.playbook -> collect -> skills.judge -> (LLM only where rules are unsure) -> guard -> answer
  mitigation adds: dry run -> apply -> wait for rollout -> submit   (approval is automatic here: there is no person
  in a benchmark loop, which is recorded in the trace so results are not mistaken for the product's behaviour)

AIOpsLab calls get_action(observation) once per step and expects one API call in a markdown code block back.
Every decision is written to self.trace, so a run can be explained step by step afterwards.
"""
from __future__ import annotations

import json
import re

from . import evidence as evi
from . import guard, skills
from .llm import LLM, NoLLM

NEXT = "Please take the next action"


def _code(call: str) -> str:
    return f"```\n{call}\n```"


def _shell(cmd: str, timeout: int = 120) -> str:
    return _code(f'exec_shell("{cmd}", {timeout})')


def task_type(apis: dict[str, str], instructions: str) -> str:
    submit = " ".join(v for k, v in apis.items() if "submit" in k) + instructions
    if "has_anomaly" in submit or 'submit("Yes")' in submit:
        return "detection"
    if "faulty_components" in submit:
        return "localization"
    if "system_level" in submit:
        return "analysis"
    return "mitigation"


class AIOpsOneAgent:
    def __init__(self, llm: LLM | None = None):
        self.llm = llm or NoLLM()
        self.trace: list[dict] = []

    # ---- AIOpsLab interface ----
    def init_context(self, problem_desc: str, instructions: str, apis: dict[str, str]):
        self.task = task_type(apis, instructions)
        self.ns = evi.namespace_from(problem_desc)
        self.steps = evi.playbook(self.ns)
        self.outputs: dict[str, str] = {}
        self.pending: str | None = None   # key of the command whose output arrives next
        self.queue: list[tuple[str, str]] = []
        self.answer: str | None = None
        self.trace = [{"kind": "start", "task": self.task, "namespace": self.ns, "llm": self.llm.name}]

    async def get_action(self, observation: str) -> str:
        if self.pending:
            self.outputs[self.pending] = observation.replace(NEXT, "").strip()
            self.pending = None
        # 1. evidence, one read-only command per step
        if len(self.outputs) < len(self.steps) and not self.answer:
            key, cmd = self.steps[len(self.outputs)]
            self.pending = key
            self.trace.append({"kind": "tool", "tool": key, "cmd": cmd})
            return _shell(cmd)
        # 2. decide once
        if self.answer is None:
            self.answer = self._decide()
        # 3. mitigation commands, if any, then submit
        if self.queue:
            key, cmd = self.queue.pop(0)
            self.pending = key
            self.trace.append({"kind": key, "cmd": cmd})
            return _shell(cmd, 180)
        return self.answer

    # ---- reasoning ----
    def _decide(self) -> str:
        ev = evi.collect(self.ns, self.outputs)
        v = skills.judge(ev)
        self.trace.append({"kind": "analysis", "pods": len(ev.pods), "findings": [f.__dict__ for f in ev.findings[:12]],
                           "verdict": v.__dict__})
        if self.task == "detection":
            return _code(f'submit("{"Yes" if v.anomaly else "No"}")')
        if self.task == "localization":
            culprits = v.culprits
            if v.anomaly and not v.confident:
                culprits = self._ask_culprits(ev, v)
            return _code(f"submit({json.dumps(culprits)})")
        if self.task == "analysis":
            ans = skills.analysis_answer(v)
            if ans is None:
                return _code("submit()")
            if not v.confident or v.fault_kind is None:
                ans = self._ask_analysis(ev, v)
            return _code(f"submit({json.dumps(ans)})")
        # mitigation
        plan = skills.mitigation_plan(ev, v) if v.anomaly else []
        for dry, apply in plan:
            comp = apply.split("deployment/")[1].split()[0]
            self.queue += [("dry_run", dry), ("approved_apply", apply),
                           ("verify", f"kubectl rollout status deployment/{comp} -n {self.ns} --timeout=150s")]
        self.trace.append({"kind": "plan", "steps": plan, "approval": "automatic (benchmark has no human in the loop)",
                           "escalated": bool(v.anomaly and not plan)})
        return _code("submit()")

    def _facts(self, ev: evi.Evidence) -> str:
        lines = [f"- {f.component} [{f.kind}] {f.line[:160]}" for f in ev.findings[:15]]
        return "\n".join(lines) or "- none"

    def _ask_culprits(self, ev: evi.Evidence, v: skills.Verdict) -> list[str]:
        prompt = (f"Components in namespace {ev.namespace}: {', '.join(sorted(ev.components))}\nEvidence:\n{self._facts(ev)}\n"
                  "Which component is the root cause? Answer only a JSON list of component names.")
        raw = self.llm.complete([{"role": "user", "content": prompt}])
        names = re.findall(r'"([a-z0-9-]+)"', raw)
        culprits, why = guard.check_culprits(names, ev, v)
        self.trace.append({"kind": "llm", "ask": "culprits", "raw": raw[:300], "guard": why})
        return culprits

    def _ask_analysis(self, ev: evi.Evidence, v: skills.Verdict) -> dict:
        prompt = (f"Evidence from a Kubernetes application:\n{self._facts(ev)}\n"
                  f"Pick system_level from {skills.SYSTEM_LEVELS} and fault_type from {skills.FAULT_TYPES}. "
                  'Answer only JSON like {"system_level": "...", "fault_type": "..."}.')
        raw = self.llm.complete([{"role": "user", "content": prompt}])
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            ans = json.loads(m.group()) if m else {}
        except json.JSONDecodeError:
            ans = {}
        out, why = guard.check_analysis(ans, v)
        self.trace.append({"kind": "llm", "ask": "analysis", "raw": raw[:300], "guard": why})
        return out
