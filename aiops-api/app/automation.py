"""User-built automation: the rules behind skills, skill sets, runbooks and playbooks people write themselves.

  skill      what the AI investigates: the incident kinds that trigger it, the read-only tools it may call, and
             instructions in the team's own words. A custom skill rides on the built-in investigation for that kind
             and adds its tools and instructions on top, so it can never do less than the built-in one.
  skill set  a named group of skills for part of the estate (services or hosts by name pattern, e.g. "pay-*").
             An incident there is investigated only with the set's skills, unless none of them fits its kind.
  runbook    a fix the team already knows: kind + service + fix type, with steps. Found the same way as runbooks
             the AI learned from good ratings, so the AI reuses it instead of starting over.
  playbook   what to do when an incident happens: hand it to a team, and escalate if nobody approves in time.
             A playbook never applies a fix: every fix still needs a person to approve it.

Pure: no database, no LLM. The routes and the agent call these.
"""
from __future__ import annotations

import fnmatch
import re

KINDS = ["error_rate", "latency", "traffic_drop", "host_cpu", "host_mem", "host_disk", "host_down", "auth_bruteforce",
         "log_errors", "container_cpu", "container_mem", "container_down"]
SEVERITY = {"minor": 1, "major": 2, "critical": 3}
FIX_TYPES = ["rollback_deployment", "restart_service", "restart_instance", "block_ip", "manual"]

# every tool is read-only; `on` says which entity the incident must be about for the tool to apply
TOOL_CATALOG = {
    "getMetric": {"label": "Service metric now vs before", "on": "service", "reads": True},
    "searchTraces": {"label": "Slow or failing traces", "on": "service", "reads": True},
    "searchLogs": {"label": "Error and warning logs", "on": "service", "reads": True},
    "getErrorRateByVersion": {"label": "Errors by release version", "on": "service", "reads": True},
    "getDeployHistory": {"label": "Recent deploys", "on": "service", "reads": True},
    "findSilentServices": {"label": "Services that went quiet", "on": "service", "reads": True},
    "getTopSourceIPs": {"label": "Busiest source IPs in logs", "on": "service", "reads": True},
    "searchLoadBalancerLogs": {"label": "Load balancer access log", "on": "any", "reads": True},
    "searchFirewallLogs": {"label": "Firewall log", "on": "any", "reads": True},
    "getHostMetrics": {"label": "Host CPU, memory, disk", "on": "host", "reads": True},
    "getTopProcesses": {"label": "Busiest processes on the host", "on": "host", "reads": True},
    "getContainerStats": {"label": "Container CPU and memory", "on": "any", "reads": True},
}
_ARG = {"getMetric": lambda e: {"entity": e, "metric": "error_rate"}, "getDeployHistory": lambda e: {"service": e}}


def tool_args(tool: str, entity: str, entity_type: str) -> dict | None:
    t = TOOL_CATALOG.get(tool)
    if not t:
        return None
    if t["on"] == "any":
        return {}
    if t["on"] != entity_type:
        return None
    return _ARG.get(tool, lambda e: {t["on"]: e})(entity)


def skill_id(name: str) -> str:
    return "custom-" + re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")[:48]


def validate_skill(b: dict) -> list[str]:
    errs = []
    if not str(b.get("name") or "").strip():
        errs.append("name is required")
    kinds = b.get("kinds") or []
    if not kinds:
        errs.append("pick at least one incident kind that triggers the skill")
    errs += [f"unknown incident kind '{k}'" for k in kinds if k not in KINDS]
    errs += [f"'{t}' is not one of the read-only tools" for t in b.get("tools") or [] if t not in TOOL_CATALOG]
    if len(str(b.get("instructions") or "")) > 2000:
        errs.append("instructions are limited to 2000 characters")
    return errs


def _in_scope(entity: str, scope: str) -> bool:
    return any(fnmatch.fnmatch(entity, p.strip()) for p in (scope or "").split(",") if p.strip())


def eligible_skills(kind: str, entity: str, skills: list[dict], skill_sets: list[dict]) -> list[str]:
    fit = [s["id"] for s in skills if s.get("enabled", True) and kind in (s.get("kinds") or [])]
    for st in skill_sets:
        if st.get("enabled", True) and _in_scope(entity, st.get("scope", "")):
            narrowed = [i for i in fit if i in (st.get("skills") or [])]
            if narrowed:
                return narrowed
    return fit


def base_skill(kind: str, skills: list[dict]) -> str | None:
    return next((s["id"] for s in skills if s.get("builtin") and kind in (s.get("kinds") or [])), None)


def choose_skill(eligible: list[str], llm_choice: str | None, rule: str) -> tuple[str, str]:
    """The LLM picks among the skills the team allows for this incident; anything else falls back to a rule."""
    if not eligible:
        return rule, f"every skill for this kind is switched off - the built-in {rule} investigates so the incident is not left alone"
    if llm_choice in eligible:
        return llm_choice, "selected by LLM"
    if rule in eligible:
        return rule, "LLM unavailable/invalid - rule-based selection by signal type"
    return eligible[0], f"the skill set for this service allows only {', '.join(eligible)}"


def extra_tools(skill_tools: list[str], base_tools: list[str]) -> list[str]:
    return [t for t in skill_tools if t not in base_tools]


def runbook_signature(b: dict) -> str:
    return f"{b['kind']}|{(b.get('service') or '').strip()}|{b['action_type']}"


def validate_runbook(b: dict) -> list[str]:
    errs = []
    if not str(b.get("title") or "").strip():
        errs.append("title is required")
    if b.get("kind") not in KINDS:
        errs.append(f"unknown incident kind '{b.get('kind')}'")
    if not str(b.get("service") or "").strip():
        errs.append("service (or host) is required: the runbook is found by kind + service + fix")
    if b.get("action_type") not in FIX_TYPES:
        errs.append(f"'{b.get('action_type')}' is not a fix SIT-AIOPS can dry-run")
    steps = [s for s in b.get("steps") or [] if str(s).strip()]
    if not steps:
        errs.append("add at least one step")
    return errs


def validate_playbook(b: dict) -> list[str]:
    errs = []
    if not str(b.get("name") or "").strip():
        errs.append("name is required")
    tr, ac = b.get("trigger") or {}, b.get("actions") or {}
    errs += [f"unknown incident kind '{k}'" for k in tr.get("kinds") or [] if k not in KINDS]
    if tr.get("min_severity") and tr["min_severity"] not in SEVERITY:
        errs.append(f"unknown severity '{tr['min_severity']}'")
    esc = ac.get("escalate_after_min")
    if esc is not None and not (isinstance(esc, int) and 1 <= esc <= 1440):
        errs.append("escalate after must be 1 to 1440 minutes")
    if ac.get("auto_apply"):
        errs.append("a playbook cannot apply a fix on its own: every fix needs a person's approval")
    return errs


def match_playbooks(inc: dict, playbooks: list[dict]) -> list[dict]:
    out = []
    for p in playbooks:
        if not p.get("enabled", True):
            continue
        tr = p.get("trigger") or {}
        if tr.get("kinds") and inc["kind"] not in tr["kinds"]:
            continue
        if tr.get("min_severity") and SEVERITY.get(inc.get("severity"), 0) < SEVERITY[tr["min_severity"]]:
            continue
        if tr.get("entity") and not _in_scope(inc.get("entity") or "", tr["entity"]):
            continue
        out.append(p)
    return out


def due_escalations(waiting: list[dict], playbooks: list[dict], escalated: set, now: float) -> list[tuple[int, int]]:
    out = []
    for inc in waiting:
        if inc.get("status") != "awaiting_approval" or not inc.get("analyzed_at"):
            continue
        for p in match_playbooks(inc, playbooks):
            if inc["analyzed_at"] < (p.get("since") or 0):   # waiting before the playbook existed: not its job
                continue
            mins = (p.get("actions") or {}).get("escalate_after_min")
            if mins and now - inc["analyzed_at"] >= mins * 60 and (inc["id"], p["id"]) not in escalated:
                out.append((inc["id"], p["id"]))
    return out
