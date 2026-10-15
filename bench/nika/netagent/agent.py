"""The agent NIKA runs. Only glue lives here: call NIKA's MCP tools, hand the text to evidence/skills, write the report.

Diagnosis, step by step (the same every time, like an AIOps One skill playbook):
  1. pingmesh across all endpoints          -> who cannot reach whom (symptoms)
  2. one read-only probe on every device     -> addresses, links, routes, gateway, resolver, qdisc, firewall, CPU, DNS, BGP
  3. one DNS lookup per (client, DNS server) -> does name resolution work, and how fast
  4. rules (skills.py)                       -> findings, strongest first
Submission maps the strongest findings to the catalog NIKA hands over. No LLM is involved, and nothing reads NIKA's
ground truth: the agent sees only what the MCP tools return.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from agent.protocols import DIAGNOSIS, SUBMISSION
from agent.utils.loggers import MessageLogger, tool_event_payload
from agent.utils.mcp_client import load_session_mcp_config
from agent.utils.two_phase import TwoPhaseAgent
from nika.utils.session import Session

from . import evidence, skills

CLIENT_HINT = re.compile(r"client|pc|host", re.I)


def tool_text(result: Any) -> str:
    """MCP tool output (a string, or a list of content blocks) as plain text."""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return "\n".join(str(b.get("text", "")) if isinstance(b, dict) else str(b) for b in result)
    return str(result)


class AIOpsOneNetAgent(TwoPhaseAgent):
    def __init__(self, session_id: str, model: str = "rules", max_steps: int = 20, stream_output: bool = True):
        self.session_id = session_id
        self.model = model
        self.max_steps = max_steps
        self.stream_output = stream_output
        self.session = Session()
        self.session.load_running_session(session_id=session_id)
        self.trace_dir = self.session.session_dir
        self.findings: list[skills.Finding] = []
        self.symptoms: list[str] = []
        self._n = 0

    async def _tools(self, phase: str) -> dict[str, Any]:
        cfg = load_session_mcp_config(self.session_id, self.session.scenario_name, phase=phase)
        return {t.name: t for t in await MultiServerMCPClient(connections=cfg).get_tools()}

    async def _call(self, log: MessageLogger, tools: dict, name: str, args: dict) -> str:
        """Call one tool and log it in NIKA's trace format, so NIKA counts our steps like any agent's."""
        self._n += 1
        cid = f"net-{self._n}"
        log.log("tool_start", tool_event_payload(name=name, input=args, tool_call_id=cid))
        try:
            out = tool_text(await tools[name].ainvoke(args))
        except Exception as e:  # a failed probe is evidence too (e.g. a node that is gone); keep going
            out = f"tool_error: {e}"
        log.log("tool_end", tool_event_payload(name=name, input=args, tool_call_id=cid, output=out, output_type="str"))
        return out

    async def diagnose(self, task_description: str) -> str:
        log = MessageLogger(phase=DIAGNOSIS, session_dir=self.trace_dir)
        log.log("llm_start", {"messages": {"role": "user", "content": task_description}, "model": {"name": self.model}})
        tools = await self._tools(DIAGNOSIS)

        mesh: dict = {}
        if "run_pingmesh_snapshot" in tools:
            try:
                mesh = json.loads(await self._call(log, tools, "run_pingmesh_snapshot", {"count": 3}))
            except (json.JSONDecodeError, TypeError):
                mesh = {}
        self.symptoms = skills.symptoms(mesh)

        names = device_names(self.session_id) or sorted((mesh.get("endpoints") or {}).keys())
        devices = {}
        for n in names:
            out = await self._call(log, tools, "exec_shell", {"host_name": n, "command": evidence.device_probe(), "timeout": 20})
            devices[n] = evidence.parse_device(n, out)

        clients = {n for n, d in devices.items() if not d.is_router and not d.dns_server and CLIENT_HINT.search(n)}
        dns = []
        for server in [d for d in devices.values() if d.dns_server and d.dns_names and d.addrs]:
            for c in sorted(clients)[:2]:
                ip = str(server.addrs[0].ip)
                out = await self._call(log, tools, "exec_shell",
                                       {"host_name": c, "command": evidence.dns_probe(ip, server.dns_names[0]), "timeout": 15})
                dns.append(evidence.parse_dns(c, ip, server.dns_names[0], out))

        self.findings = skills.analyse(devices, dns, clients)
        report = render_report(self.findings, self.symptoms, devices, dns)
        log.log("llm_end", {"text": report})
        return report

    async def submit(self, diagnosis_report: str, context: dict[str, Any]) -> str:
        log = MessageLogger(phase=SUBMISSION, session_dir=self.trace_dir)
        answer = skills.submission(self.findings, self.symptoms, context)
        tools = await self._tools(SUBMISSION)
        result = await self._call(log, tools, "submit", answer)
        log.log("llm_end", {"text": f"submitted {answer}"})
        return f"Submitted: {answer} -> {result[:200]}"


def device_names(session_id: str) -> list[str]:
    """Every running device in the lab, from NIKA's own container list (names only; no fault information)."""
    try:
        from nika.workflows.session.containers import list_session_containers
        _sid, _lab, rows = list_session_containers(session_id)
    except Exception:
        return []
    return sorted({str(r.get("name") or "").strip() for r in rows} - {""})


def render_report(findings: list[skills.Finding], symptom_lines: list[str], devices: dict, dns: list) -> str:
    lines = ["# Network diagnosis (AIOps One, rule playbook)", ""]
    lines.append(f"Checked {len(devices)} devices: " + ", ".join(sorted(devices)) + ".")
    lines.append("")
    lines.append("## Symptoms (pingmesh)")
    lines += [f"- {s}" for s in symptom_lines[:15]] or ["- none: every endpoint reaches every other"]
    lines += ["", "## DNS checks"]
    lines += [f"- {c.client} -> {c.server_ip} ({c.name}): direct={'ok' if c.direct_ok else 'fail'}"
              f"{f' {c.direct_ms} ms' if c.direct_ms is not None else ''}, via resolver={'ok' if c.resolver_ok else 'fail'}"
              f"{f' {c.resolver_ms} ms' if c.resolver_ms is not None else ''}" for c in dns] or ["- no DNS server found"]
    lines += ["", "## Findings (strongest first)"]
    if findings:
        lines += [f"- [{f.weight}] {f.fault} at {f.node}{'/' + f.iface if f.iface else ''}: {f.evidence}" for f in findings]
    else:
        lines.append("- no device shows a fault")
    lines += ["", "## Conclusion"]
    if findings:
        top = findings[0]
        lines.append(f"Root cause: {top.fault} on {top.node}{'/' + top.iface if top.iface else ''}. Evidence: {top.evidence}.")
    elif symptom_lines:
        lines.append("The network shows symptoms, but no device check explains them; root cause not localised.")
    else:
        lines.append("No anomaly: reachability, gateways, resolvers, DNS, firewalls, queues and CPU all look normal.")
    return "\n".join(lines)
