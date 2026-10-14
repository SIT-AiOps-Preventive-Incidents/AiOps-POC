"""Skills: turn evidence into an answer for each AIOpsLab task type.

The rules here are the agent's own judgement - general SRE reasoning about symptoms, never knowledge of which fault a
benchmark problem injects. The LLM is consulted only where rules are unsure (see agent.py), and guard.py checks it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .evidence import Evidence, data_store_of

SYSTEM_LEVELS = ["Hardware", "Operating System", "Virtualization", "Application"]
FAULT_TYPES = ["Misconfiguration", "Code Defect", "Authentication Issue", "Network/Storage Issue", "Operation Error",
               "Dependency Problem"]
KIND_TO_FAULT = {"auth": "Authentication Issue", "config": "Misconfiguration", "network": "Network/Storage Issue",
                 "storage": "Network/Storage Issue", "crash": "Code Defect"}


@dataclass
class Verdict:
    anomaly: bool
    culprits: list[str]
    fault_kind: str | None   # strongest kind of trouble seen
    confident: bool          # rules alone are sure; otherwise ask the LLM
    reason: str


def judge(ev: Evidence) -> Verdict:
    if not ev.findings:
        return Verdict(False, [], None, True, "every pod healthy, no warning events, no error lines in logs")
    # the strongest specific sign wins; "unhealthy" alone only says something is wrong, not what
    for kind in ("auth", "storage", "config", "network", "crash"):
        hits = ev.by_kind(kind)
        if not hits:
            continue
        culprits = []
        for f in hits:
            # an application failing to authenticate (or reach storage) points at the data store it talks to
            target = data_store_of(f.component, ev.components) if kind in ("auth", "storage") else None
            culprits.append(target or f.component)
        culprits = sorted(set(culprits))
        return Verdict(True, culprits, kind, len(culprits) == 1, f"{len(hits)} {kind} sign(s), e.g. {hits[0].line[:120]}")
    unhealthy = sorted({f.component for f in ev.by_kind("unhealthy")})
    return Verdict(True, unhealthy, None, False, f"unhealthy without a clear cause: {', '.join(unhealthy)}")


def analysis_answer(v: Verdict) -> dict | None:
    if not v.anomaly:
        return None
    return {"system_level": "Application", "fault_type": KIND_TO_FAULT.get(v.fault_kind, "Code Defect")}


def mitigation_plan(ev: Evidence, v: Verdict) -> list[tuple[str, str]]:
    """(dry-run command, apply command) pairs. Only changes AIOps One also allows: restart or roll back a workload.
    Anything else (re-granting database users, changing data) is left to a person - the agent says so and stops."""
    plan = []
    for comp in v.culprits:
        if v.fault_kind in ("config", "crash", None) and comp in ev.components and not _is_data_store(comp):
            plan.append((f"kubectl rollout history deployment/{comp} -n {ev.namespace}",
                         f"kubectl rollout undo deployment/{comp} -n {ev.namespace}"))
        elif v.fault_kind == "network" and comp in ev.components:
            plan.append((f"kubectl rollout restart deployment/{comp} -n {ev.namespace} --dry-run=server",
                         f"kubectl rollout restart deployment/{comp} -n {ev.namespace}"))
    return plan


def _is_data_store(comp: str) -> bool:
    from .evidence import DB_HINT
    return bool(DB_HINT.search(comp))
