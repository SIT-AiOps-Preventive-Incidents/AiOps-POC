"""Grounding guard: an LLM answer is accepted only if the evidence supports it - the same rule AIOps One applies
to its root-cause text. A rejected answer falls back to the rule-based one, and the reason is recorded."""
from __future__ import annotations

from .evidence import Evidence
from .skills import FAULT_TYPES, KIND_TO_FAULT, SYSTEM_LEVELS, Verdict


def check_culprits(llm_culprits: list[str], ev: Evidence, rule: Verdict) -> tuple[list[str], str]:
    known = ev.components
    named = [c for c in llm_culprits if c in known]
    if not named:
        return rule.culprits, "rejected: names no component that exists in the namespace"
    implicated = {f.component for f in ev.findings} | set(rule.culprits)
    unsupported = [c for c in named if c not in implicated]
    if unsupported:
        return rule.culprits, f"rejected: no evidence against {', '.join(unsupported)}"
    return named, "accepted"


def check_analysis(llm_answer: dict, rule: Verdict) -> tuple[dict, str]:
    level, fault = llm_answer.get("system_level"), llm_answer.get("fault_type")
    fallback = {"system_level": "Application", "fault_type": KIND_TO_FAULT.get(rule.fault_kind, "Code Defect")}
    if level not in SYSTEM_LEVELS or fault not in FAULT_TYPES:
        return fallback, "rejected: not one of the allowed values"
    if rule.fault_kind and fault != KIND_TO_FAULT[rule.fault_kind]:
        return fallback, f"rejected: evidence shows {rule.fault_kind} signs, not {fault}"
    return {"system_level": level, "fault_type": fault}, "accepted"
