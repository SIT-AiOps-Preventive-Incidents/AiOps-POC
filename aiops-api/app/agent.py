"""Agentic RCA.

  1. Classify + pick a skill (LLM, validated against the skill registry; rule fallback)
  2. Check incident memory for a matching runbook
  3. Run the skill's read-only tools (getMetric, searchTraces, searchLogs, getDeployHistory, ...)
  4. Deterministic analyzers turn raw evidence into facts + allow-listed action candidates
  5. LLM (DevOps specialist role) writes root cause, summary, confidence and runbook from those facts
  6. Dry-run every candidate fix (read-only) and rank by whether it is safe to apply
  7. Save, notify the owner, wait for approval - nothing changes before that
"""
import asyncio
import json
import re
import time
from collections import Counter

from . import db, llm, notify, remediation, servicemap
from . import telemetry as tm

SKILLS = {
    "service-error-analysis": {
        "category": "Service", "name": "Service error analysis", "kinds": ["error_rate"],
        "description": "Failure-rate spikes in a service: trace error origin, error logs, version/commit correlation.",
        "tools": ["getMetric", "searchTraces", "searchLoadBalancerLogs", "getErrorRateByVersion", "getDeployHistory",
                  "searchLogs"]},
    "service-latency-analysis": {
        "category": "Service", "name": "Service latency analysis", "kinds": ["latency"],
        "description": "Response-time degradation: slow-trace self-time breakdown, warning logs, recent changes.",
        "tools": ["getMetric", "searchTraces", "searchLoadBalancerLogs", "searchLogs", "getDeployHistory"]},
    "infra-resource-analysis": {
        "category": "Infrastructure", "name": "Infrastructure resource analysis",
        "kinds": ["host_cpu", "host_mem", "host_disk", "host_down"],
        "description": "Host saturation or outage: host metrics, per-container usage, logs of the busiest workload.",
        "tools": ["getHostMetrics", "getContainerStats", "getTopProcesses", "searchLogs", "getDeployHistory"]},
    "security-auth-analysis": {
        "category": "Security", "name": "Security / authentication analysis", "kinds": ["auth_bruteforce"],
        "description": "Suspicious authentication activity: firewall + app logs, failed-login bursts, source IP concentration.",
        "tools": ["searchFirewallLogs", "searchLogs", "getTopSourceIPs", "getMetric"]},
}

KIND_LABEL = {"error_rate": "Failure rate increase", "latency": "Response time degradation",
              "host_cpu": "CPU saturation", "host_mem": "Memory saturation", "host_disk": "Low disk space",
              "host_down": "Host unavailable", "auth_bruteforce": "Suspicious login activity"}

APP_CONTAINERS_EXCLUDE = {"ollama", "aiops-api", "prometheus", "loki", "tempo", "grafana", "otel-collector",
                          "node-exporter", "edge-fw", "edge-lb", "loadgen"}

_sem = asyncio.Semaphore(1)  # one LLM-heavy analysis at a time on a CPU box


def rule_skill(kind: str) -> str:
    return next(k for k, s in SKILLS.items() if kind in s["kinds"])


def lessons(skill: str) -> list[str]:
    rows = db.q("SELECT feedback FROM incidents WHERE skill=? AND feedback IS NOT NULL AND feedback!='' "
                "AND score IS NOT NULL AND score<=3 ORDER BY id DESC LIMIT 3", (skill,))
    return [r["feedback"] for r in rows]


# ---------------- tools (read-only) ----------------
async def t_getMetric(entity: str, metric: str, minutes: int = 15):
    expr = tm.svc_expr(entity, metric)
    now_v = await tm.prom_value(expr)
    series = await tm.prom_range(expr, minutes=minutes, step=30)
    pts = [p[1] for p in (series[0]["points"] if series else []) if p[1] is not None]
    base = pts[: max(1, len(pts) // 2)]
    return {"metric": metric, "service": entity, "current": now_v,
            "baseline_avg": round(sum(base) / len(base), 4) if base else None,
            "max": max(pts) if pts else None, "samples": len(pts)}


async def t_getErrorRateByVersion(service: str):
    return {"service": service, "by_version": await tm.error_rate_by_version(service)}


async def t_getDeployHistory(service: str | None = None, minutes: int = 120):
    since = time.time() - minutes * 60
    if service:
        rows = db.q("SELECT * FROM deployments WHERE ts>=? AND service=? ORDER BY ts DESC", (since, service))
    else:
        rows = db.q("SELECT * FROM deployments WHERE ts>=? ORDER BY ts DESC LIMIT 20", (since,))
    return {"window_min": minutes, "deployments": rows}


async def t_searchTraces(service: str, mode: str = "error", minutes: int = 5):
    cond = "status = error" if mode == "error" else f"duration > {int(db.fsetting('p95_threshold_ms'))}ms"
    q = f'{{ resource.service.name = "{service}" && {cond} }}'
    found = await tm.tempo_search(q, minutes=minutes, limit=20)
    origins, inst, msgs, selft, samples = Counter(), Counter(), Counter(), Counter(), []
    for tr in found[:6]:
        spans = await tm.tempo_trace(tr["traceID"])
        if not spans:
            continue
        if mode == "error":
            for o in tm.error_origin(spans):
                origins[o["service"]] += 1
                inst[o["instance"]] += 1
                if o["status_msg"]:
                    msgs[o["status_msg"][:160]] += 1
        else:
            for svc, ms in tm.self_time(spans).items():
                selft[svc] += ms
        samples.append({"trace_id": tr["traceID"], "root": tr.get("rootTraceName"), "duration_ms": tr.get("durationMs")})
    out = {"query": q, "matched": len(found), "analyzed": len(samples), "samples": samples[:5]}
    if mode == "error":
        out["error_origin_services"] = dict(origins.most_common())
        out["error_origin_instances"] = dict(inst.most_common())
        out["error_messages"] = dict(msgs.most_common(3))
    else:
        n = max(len(samples), 1)
        out["avg_self_time_ms_by_service"] = {k: round(v / n, 1) for k, v in selft.most_common()}
    return out


async def t_searchLogs(service: str, levels: str = "ERROR|WARN.*", contains: str = "", minutes: int = 10):
    lf = f'|= "{contains}"' if contains else ""
    sel = f'{{service_name="{service}"}}'
    if levels:
        lf = (lf + f' | severity_text=~"{levels}"').strip()
    logs = await tm.loki_logs(sel, minutes=minutes, limit=200, line_filter=lf)
    return {"service": service, "filter": lf, "count": len(logs), "top_patterns": tm.top_messages(logs, 4),
            "latest": [{"ts": l["ts"], "level": l["level"], "line": l["line"], "trace_id": l["trace_id"]}
                       for l in logs[:5]]}


async def t_getTopSourceIPs(service: str, contains: str = "failed login", minutes: int = 5):
    logs = await tm.loki_logs(f'{{service_name="{service}"}}', minutes=minutes, limit=1000,
                              line_filter=f'|= "{contains}"')
    ips = Counter(m.group(1) for l in logs if (m := re.search(r"ip=(\S+)", l["line"])))
    users = Counter(m.group(1) for l in logs if (m := re.search(r"user=(\S+)", l["line"])))
    total = sum(ips.values()) or 1
    return {"events": len(logs), "top_ips": [{"ip": ip, "count": c, "share": round(c / total, 2)}
                                             for ip, c in ips.most_common(5)],
            "targeted_users": dict(users.most_common(5))}


def _p95(xs: list[float]) -> float | None:
    xs = sorted(xs)
    return round(xs[int(0.95 * (len(xs) - 1))] * 1000, 1) if xs else None


async def t_searchLoadBalancerLogs(minutes: int = 5):
    """Edge load balancer access logs: status and upstream response time per backend instance."""
    logs = await tm.edge_logs("edge-lb", minutes=minutes, limit=4000)
    ipmap = await tm.container_ip_map()
    by_up: dict[str, dict] = {}
    for l in logs:
        addr = (l.get("upstream") or "-").split(",")[0].strip()
        name = ipmap.get(addr.split(":")[0], addr)
        st = str(l.get("upstream_status") or l.get("status"))
        d = by_up.setdefault(name, {"requests": 0, "5xx": 0, "4xx": 0, "rt": []})
        d["requests"] += 1
        d["5xx"] += st.startswith("5")
        d["4xx"] += st.startswith("4")
        try:
            d["rt"].append(float(str(l.get("upstream_rt")).split(",")[0]))
        except ValueError:
            pass
    out = {}
    for k, d in by_up.items():
        out[k] = {"requests": d["requests"], "5xx": d["5xx"], "4xx": d["4xx"],
                  "error_rate": round(d["5xx"] / d["requests"], 4) if d["requests"] else 0,
                  "p95_upstream_ms": _p95(d["rt"])}
    total5 = sum(v["5xx"] for v in out.values())
    return {"device": "edge-lb", "window_min": minutes, "requests": len(logs), "upstream_5xx": total5,
            "by_upstream": dict(sorted(out.items(), key=lambda kv: -kv[1]["5xx"])),
            "status_counts": dict(Counter(str(l.get("status")) for l in logs).most_common(6))}


async def t_searchFirewallLogs(minutes: int = 5, path: str = ""):
    """Edge firewall access logs: allow/deny decisions and per-source-IP behaviour."""
    logs = await tm.edge_logs("edge-firewall", minutes=minutes, limit=4000,
                              line_filter=f'|= "{path}"' if path else "")
    by_ip: dict[str, Counter] = {}
    for l in logs:
        c = by_ip.setdefault(l.get("src_ip") or "-", Counter())
        c["requests"] += 1
        c[f"status_{l.get('status')}"] += 1
        c[l.get("action", "?")] += 1
    top = sorted(by_ip.items(), key=lambda kv: -kv[1]["requests"])[:5]
    total = len(logs) or 1
    return {"device": "edge-firewall", "window_min": minutes, "path_filter": path, "requests": len(logs),
            "actions": dict(Counter(l.get("action") for l in logs)),
            "top_sources": [{"ip": ip, "share": round(c["requests"] / total, 2), **dict(c)} for ip, c in top]}


async def t_getHostMetrics(host: str):
    out = {"host": host}
    for m in ("cpu", "mem", "disk", "load", "up"):
        v = await tm.prom_value(tm.host_expr(host, m))
        out[m] = round(v, 2) if v is not None else None
    return out


async def t_getTopProcesses(host: str):
    """Latest process list pushed by the AIOps host agent on that machine."""
    logs = await tm.loki_logs('{service_name="aiops-agent"}', minutes=3, limit=20,
                              line_filter=f'|= "\\"host\\": \\"{host}\\""')
    for lg in logs:
        try:
            d = json.loads(lg["line"])
            return {"host": host, "ts": lg["ts"], "processes": d.get("processes", [])}
        except ValueError:
            continue
    return {"host": host, "processes": [], "note": "no process data in the last 3 minutes"}


async def t_getContainerStats():
    stats = await tm.containers(with_stats=True)
    return {"top_by_cpu": stats[:8]}


TOOLS = {"getMetric": t_getMetric, "getErrorRateByVersion": t_getErrorRateByVersion,
         "getDeployHistory": t_getDeployHistory, "searchTraces": t_searchTraces, "searchLogs": t_searchLogs,
         "getTopSourceIPs": t_getTopSourceIPs, "getHostMetrics": t_getHostMetrics,
         "getContainerStats": t_getContainerStats, "searchLoadBalancerLogs": t_searchLoadBalancerLogs,
         "searchFirewallLogs": t_searchFirewallLogs, "getTopProcesses": t_getTopProcesses}


class Run:
    """Collects agent steps so the UI can replay the investigation."""

    def __init__(self, inc_id: int):
        self.inc_id, self.steps = inc_id, []

    def step(self, kind: str, title: str, **data):
        self.steps.append({"ts": time.time(), "kind": kind, "title": title, **data})
        db.update("incidents", self.inc_id, {"steps": self.steps})

    async def tool(self, name: str, **args):
        t0 = time.time()
        try:
            out = await TOOLS[name](**args)
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {e}"}
        self.step("tool", name, args=args, output=out, ms=int((time.time() - t0) * 1000))
        return out


# ---------------- skill playbooks: tools -> facts -> action candidates ----------------
def _prev_deploy(service: str, before_ts: float) -> dict | None:
    return db.one("SELECT * FROM deployments WHERE service=? AND ts<? ORDER BY ts DESC LIMIT 1", (service, before_ts))


def _multi_instance(service: str) -> bool:
    return len(remediation.containers_of(service)) > 1


def _lb_concentration(lb: dict) -> tuple[str | None, float]:
    """Is one backend instance producing (almost) all the 5xx behind the load balancer?"""
    ups = lb.get("by_upstream") or {}
    tot = sum(v["5xx"] for v in ups.values())
    if tot < 5:
        return None, 0.0
    name, v = max(ups.items(), key=lambda kv: kv[1]["5xx"])
    return name, v["5xx"] / tot


async def play_service_error(run: Run, sig: dict) -> tuple[dict, list]:
    ent = sig["entity"]
    await run.tool("getMetric", entity=ent, metric="error_rate")
    tr = await run.tool("searchTraces", service=ent, mode="error")
    origins = tr.get("error_origin_services") or {}
    origin = max(origins, key=origins.get) if origins else ent
    if origin != ent:
        await run.tool("getMetric", entity=origin, metric="error_rate")
    lb = None
    if _multi_instance(origin) or origin in ("edge-lb", "edge-firewall"):
        lb = await run.tool("searchLoadBalancerLogs", minutes=5)
    ver = await run.tool("getErrorRateByVersion", service=origin)
    dep = await run.tool("getDeployHistory", service=origin, minutes=60)
    logs = await run.tool("searchLogs", service=origin, levels="ERROR")
    top_log = (logs.get("top_patterns") or [{}])[0]
    thr = db.fsetting("err_threshold")
    bad = [v for v in ver.get("by_version", []) if v["error_rate"] >= thr]
    deploys = dep.get("deployments", [])
    suspect = next((d for d in deploys if bad and d["version"] == bad[0]["version"]
                    and d["commit_hash"] == bad[0]["commit"]), None) or \
        next((d for d in deploys if bad and d["version"] == bad[0]["version"]), None)
    hot_inst, hot_share = _lb_concentration(lb) if lb else (None, 0.0)
    inst_votes = tr.get("error_origin_instances") or {}
    instance_specific = bool(hot_inst and hot_share >= 0.8 and remediation.app_row(origin)
                             and hot_inst in remediation.containers_of(origin) and not suspect)
    facts = {
        "alerting_service": ent, "error_origin_service": origin, "trace_origin_votes": origins,
        "trace_origin_instances": inst_votes,
        "trace_error_messages": tr.get("error_messages"), "error_rate_by_version": ver.get("by_version"),
        "recent_deploys": [{k: d[k] for k in ("version", "commit_hash", "author", "message", "ts")} for d in deploys[:3]],
        "suspect_deploy": suspect and {k: suspect[k] for k in ("version", "commit_hash", "author", "message", "ts")},
        "top_error_log": top_log.get("example"), "top_error_log_count": top_log.get("count"),
        "lb_by_upstream": lb and lb.get("by_upstream"),
        "lb_hot_instance": hot_inst if instance_specific else None, "lb_hot_share": round(hot_share, 2),
    }
    cands = []
    if instance_specific:
        cands.append({"type": "restart_instance", "params": {"service": origin, "instance": hot_inst}})
    if suspect:
        bad_builds = {(v["version"], v["commit"]) for v in bad} | {(suspect["version"], suspect["commit_hash"])}
        good, considered = await remediation.last_known_good(origin, bad_builds)
        facts["rollback_target_search"] = considered
        if good:
            cands.append({"type": "rollback_deployment", "params": {
                "service": origin, "to_version": good["version"], "to_commit": good["commit_hash"],
                "from_version": suspect["version"], "from_commit": suspect["commit_hash"]}})
    cands.append({"type": "restart_service", "params": {"service": origin}})
    conf = 0.45 + (0.2 if origins else 0) + (0.25 if suspect or instance_specific else 0) + (0.1 if top_log else 0)
    facts["evidence_confidence"] = round(min(conf, 0.95), 2)
    return facts, cands


async def play_service_latency(run: Run, sig: dict) -> tuple[dict, list]:
    ent = sig["entity"]
    await run.tool("getMetric", entity=ent, metric="p95")
    tr = await run.tool("searchTraces", service=ent, mode="slow")
    st = tr.get("avg_self_time_ms_by_service") or {}
    origin = max(st, key=st.get) if st else ent
    lb = await run.tool("searchLoadBalancerLogs", minutes=5) if _multi_instance(origin) else None
    logs = await run.tool("searchLogs", service=origin, levels="WARN.*|ERROR")
    dep = await run.tool("getDeployHistory", service=origin, minutes=60)
    top_log = (logs.get("top_patterns") or [{}])[0]
    facts = {"alerting_service": ent, "slowest_service_by_self_time": origin, "self_time_ms": st,
             "top_warning_log": top_log.get("example"), "top_warning_log_count": top_log.get("count"),
             "recent_deploys": [{k: d[k] for k in ("version", "commit_hash", "message", "ts")}
                                for d in dep.get("deployments", [])[:3]],
             "lb_by_upstream": lb and lb.get("by_upstream")}
    cands = [{"type": "restart_service", "params": {"service": origin}}]
    facts["evidence_confidence"] = round(0.5 + (0.25 if st else 0) + (0.15 if top_log else 0), 2)
    return facts, cands


async def play_infra(run: Run, sig: dict) -> tuple[dict, list]:
    host = sig["entity"]
    hm = await run.tool("getHostMetrics", host=host)
    if tm.host_agent(host) == "aiops-agent":
        tp = await run.tool("getTopProcesses", host=host)
        procs = tp.get("processes") or []
        hog = procs[0] if procs else None
        facts = {"host": host, "host_metrics": hm, "top_processes": procs[:5],
                 "busiest_workload": hog and {"name": hog["name"], "cpu_pct": hog["cpu"], "mem_pct": hog["mem"]},
                 "remote_host": True}
        facts["evidence_confidence"] = 0.7 if hog else 0.5
        # Remote machines are observe-only: the platform never executes anything on them.
        return facts, [{"type": "manual", "params": {}}]
    cs = await run.tool("getContainerStats")
    apps = {c: a["service_name"] for a in db.q("SELECT container, service_name FROM apps")
            for c in remediation._split(a["container"]) or [a["service_name"]]}
    top = [c for c in cs.get("top_by_cpu", []) if c.get("name") not in APP_CONTAINERS_EXCLUDE]
    hog = top[0] if top else None
    facts = {"host": host, "host_metrics": hm, "top_containers": cs.get("top_by_cpu", [])[:5], "busiest_workload": hog}
    cands = []
    if hog and hog.get("name") in apps:
        svc = apps[hog["name"]]
        logs = await run.tool("searchLogs", service=svc, levels="WARN.*|ERROR")
        await run.tool("getDeployHistory", service=svc, minutes=60)
        facts["busiest_workload_logs"] = [p["example"] for p in logs.get("top_patterns", [])[:3]]
        if sig["kind"] in ("host_cpu", "host_mem") and hog["cpu_pct"] > 40:
            if _multi_instance(svc):
                cands.append({"type": "restart_instance", "params": {"service": svc, "instance": hog["name"]}})
            else:
                cands.append({"type": "restart_service", "params": {"service": svc}})
    cands.append({"type": "manual", "params": {}})
    facts["evidence_confidence"] = 0.8 if len(cands) > 1 else 0.5
    return facts, cands


async def play_security(run: Run, sig: dict) -> tuple[dict, list]:
    ent = sig["entity"]
    fw = await run.tool("searchFirewallLogs", minutes=5, path="/api/login")
    logs = await run.tool("searchLogs", service=ent, levels="", contains="failed login", minutes=5)
    ips = await run.tool("getTopSourceIPs", service=ent)
    await run.tool("getMetric", entity=ent, metric="rps")
    top = (ips.get("top_ips") or [{}])[0]
    fw_top = (fw.get("top_sources") or [{}])[0]
    facts = {"service": ent, "failed_logins_5m": ips.get("events"), "top_source_ips": ips.get("top_ips"),
             "targeted_users": ips.get("targeted_users"), "sample": [l["line"] for l in logs.get("latest", [])[:3]],
             "firewall_login_requests_5m": fw.get("requests"), "firewall_top_sources": fw.get("top_sources"),
             "firewall_actions": fw.get("actions")}
    cands = []
    if top.get("ip") and top.get("share", 0) >= 0.5:
        cands.append({"type": "block_ip", "params": {"ip": top["ip"], "incident": sig.get("incident_id")}})
    cands.append({"type": "manual", "params": {}})
    agree = fw_top.get("ip") == top.get("ip")
    facts["firewall_confirms_source"] = agree
    facts["evidence_confidence"] = round(min(0.95, 0.45 + 0.35 * top.get("share", 0) + (0.15 if agree else 0)), 2)
    return facts, cands


PLAYBOOKS = {"service-error-analysis": play_service_error, "service-latency-analysis": play_service_latency,
             "infra-resource-analysis": play_infra, "security-auth-analysis": play_security}


def signature(kind: str, facts: dict, action: dict) -> str:
    target = action.get("params", {}).get("service") or facts.get("error_origin_service") or \
        facts.get("slowest_service_by_self_time") or facts.get("service") or facts.get("host") or ""
    return f"{kind}|{target}|{action['type']}"


def _pct(v) -> str:
    return f"{v * 100:.0f}%" if isinstance(v, (int, float)) else "?"


def _hhmm(ts) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "?"


def findings(kind: str, facts: dict) -> list[str]:
    """Evidence restated as plain sentences - small models reason far better over these than raw JSON."""
    f, out = facts, []
    if kind == "error_rate":
        o = f["error_origin_service"]
        votes = f.get("trace_origin_votes") or {}
        if votes:
            out.append(f"The alert fired on {f['alerting_service']}, but distributed traces show the failing span "
                       f"originates in {o} ({votes.get(o, 0)} of {sum(votes.values())} sampled error traces).")
        vers = f.get("error_rate_by_version") or []
        if vers:
            out.append(f"Current failure rate of {o} by running version: " +
                       ", ".join(f"v{v['version']} (commit {v['commit']}) {_pct(v['error_rate'])}" for v in vers) + ".")
        sd = f.get("suspect_deploy")
        if sd:
            out.append(f"{o} v{sd['version']} (commit {sd['commit_hash']}) was deployed at {_hhmm(sd['ts'])} by "
                       f"{sd['author']} with message '{sd['message']}'. The errors only occur on this version.")
        else:
            out.append(f"No deployment of {o} in the last 60 minutes matches the failing version.")
        if f.get("top_error_log"):
            out.append(f"Most frequent error log in {o} ({f.get('top_error_log_count')}x): {f['top_error_log']}")
        ups = f.get("lb_by_upstream") or {}
        if ups:
            out.append("Load balancer logs, 5xx by backend instance (5 min): " +
                       ", ".join(f"{k} {v['5xx']}/{v['requests']} ({_pct(v['error_rate'])})" for k, v in ups.items()) + ".")
        if f.get("lb_hot_instance"):
            out.append(f"{_pct(f['lb_hot_share'])} of the 5xx come from instance {f['lb_hot_instance']} only; "
                       f"the other {o} instances are healthy, so this is an instance fault, not a code change.")
    elif kind == "latency":
        o = f["slowest_service_by_self_time"]
        st = f.get("self_time_ms") or {}
        out.append(f"Average self time per slow request by service: " +
                   ", ".join(f"{k} {v:.0f} ms" for k, v in st.items()) + f". {o} dominates.")
        if f.get("top_warning_log"):
            out.append(f"Most frequent warning log in {o} ({f.get('top_warning_log_count')}x): {f['top_warning_log']}")
        out.append("Recent deployments of " + o + ": " + (", ".join(
            f"v{d['version']} at {_hhmm(d['ts'])}" for d in f.get("recent_deploys", [])) or "none in the last 60 minutes") + ".")
    elif kind == "auth_bruteforce":
        ips = f.get("top_source_ips") or []
        out.append(f"{f.get('failed_logins_5m')} failed logins on {f['service']} in the last 5 minutes.")
        if ips:
            out.append(f"Source IP {ips[0]['ip']} produced {_pct(ips[0]['share'])} of them; targeted users: "
                       + ", ".join(f.get("targeted_users") or {}) + ".")
        fwt = (f.get("firewall_top_sources") or [{}])[0]
        if fwt.get("ip"):
            out.append(f"Edge firewall saw {f.get('firewall_login_requests_5m')} requests to /api/login in 5 min; "
                       f"{fwt['ip']} sent {_pct(fwt.get('share'))} of them, all currently ALLOWED by policy.")
    else:
        hm = f.get("host_metrics") or {}
        out.append(f"Host {f.get('host')}: CPU {hm.get('cpu')}%, memory {hm.get('mem')}%, disk {hm.get('disk')}%, load {hm.get('load')}.")
        w = f.get("busiest_workload")
        if w:
            out.append(f"Busiest {'process' if f.get('remote_host') else 'workload: container'} {w['name']} at {w['cpu_pct']}% CPU.")
        if f.get("remote_host"):
            out.append("This machine is observe-only; the fix is a manual step for its owner.")
        for l in f.get("busiest_workload_logs") or []:
            out.append(f"Log from that workload: {l}")
    return out


def fallback_text(kind: str, facts: dict, action: dict) -> dict:
    a = remediation.label(action)
    if kind == "error_rate":
        sd = facts.get("suspect_deploy")
        if facts.get("lb_hot_instance"):
            rc = (f"Instance {facts['lb_hot_instance']} of {facts['error_origin_service']} is faulty "
                  f"({_pct(facts['lb_hot_share'])} of 5xx behind the load balancer): "
                  f"{facts.get('top_error_log') or 'see logs'}")
        else:
            rc = (f"Deployment v{sd['version']} (commit {sd['commit_hash']}) of {facts['error_origin_service']} introduced a "
                  f"regression: {facts.get('top_error_log') or 'see logs'}" if sd else
                  f"{facts['error_origin_service']} is failing requests: {facts.get('top_error_log') or 'see traces'}")
    elif kind == "latency":
        rc = (f"{facts['slowest_service_by_self_time']} dominates request time: "
              f"{facts.get('top_warning_log') or 'slow responses'}")
    elif kind == "auth_bruteforce":
        ip = (facts.get("top_source_ips") or [{}])[0]
        rc = f"Credential-stuffing burst from {ip.get('ip')} ({facts.get('failed_logins_5m')} failed logins in 5 min)"
    else:
        w = facts.get("busiest_workload") or {}
        rc = f"Host {facts.get('host')} saturated; busiest workload {w.get('name')} at {w.get('cpu_pct')}% CPU"
    if kind.startswith("host_"):
        w = (facts.get("busiest_workload") or {}).get("name", "the busiest process")
        steps = {"host_disk": ["Find the largest folders (e.g. `du -sh ~/* | sort -h`)", "Empty caches, old downloads and Docker images",
                               "Confirm disk use is below 80%"],
                 "host_down": ["Check the machine is powered on and on the network", "Check the agent log (~/.aiops-agent/agent.log)"]
                 }.get(kind, [f"Check whether {w} should be using this much", a, "Confirm CPU/memory return to normal"])
        return {"root_cause": rc, "summary": " ".join(findings(kind, facts)), "runbook": steps}
    return {"root_cause": rc, "summary": " ".join(findings(kind, facts)),
            "runbook": ["Confirm the evidence in the linked traces and logs", a,
                        "Watch the failure rate / latency for 5 minutes", "Open a follow-up ticket for the owning team"]}


def grounding_problems(kind: str, facts: dict, action: dict, rc: str) -> tuple[list[str], list[str]]:
    """Check an LLM root cause against the evidence (a 1.5B model will happily invent causality).
    hard = contradicts the evidence -> discard the LLM output; soft = too vague -> sharpen from evidence."""
    low, hard, soft = rc.lower(), [], []
    target = action.get("params", {}).get("service") or facts.get("service") or ""
    if kind in ("error_rate", "latency") and target and target.lower() not in low:
        hard.append(f"does not name the origin service '{target}'")
    if re.search(r"roll(ed|ing)?[ -]?back|restart(ed)?|block(ed)?", low):
        hard.append("describes the proposed remediation as if it were the cause")
    sd = facts.get("suspect_deploy")
    if kind == "error_rate" and sd and sd["version"] not in rc and sd["commit_hash"] not in rc:
        soft.append(f"does not name the faulty version {sd['version']} / commit {sd['commit_hash']}")
    if kind == "auth_bruteforce":
        ip = ((facts.get("top_source_ips") or [{}])[0]).get("ip")
        if ip and ip not in rc:
            soft.append(f"does not name the source IP {ip}")
    hot = facts.get("lb_hot_instance")
    if hot and hot not in rc:
        soft.append(f"does not name the faulty instance {hot}")
    return hard, soft


async def summarize(inc: dict, skill: str, facts: dict, action: dict, run: Run) -> dict:
    system = ("You are a senior DevOps/SRE engineer writing an incident root cause analysis for the on-call team. "
              "Base every statement ONLY on the findings. The remediation has NOT been executed yet. Reply with JSON only.")
    lessons_txt = "\n".join(f"- {l}" for l in lessons(skill)) or "- none"
    fl = findings(inc["kind"], facts)
    user = (f"Alert: {inc['title']}\n\nFindings from metrics, traces, logs and deploy history:\n" +
            "\n".join(f"{i + 1}. {x}" for i, x in enumerate(fl)) +
            f"\n\nLessons from engineers' feedback on earlier analyses:\n{lessons_txt}\n\n"
            f"Proposed fix (passed a dry run, NOT executed, waiting for the owner): {remediation.label(action)}\n\n"
            "Write JSON with keys:\n"
            '"root_cause": one sentence naming the component and what is wrong with it (the cause, not the fix),\n'
            '"summary": 2-3 sentences explaining the impact and the evidence,\n'
            '"confidence": number 0-1,\n'
            f'"runbook": 3-5 short imperative steps, the main one being: {remediation.label(action)}')
    run.step("llm", "DevOps specialist agent: summarize & recommend", prompt_chars=len(user), findings=fl)
    out, meta = await llm.chat_json(system, user, max_tokens=400)
    run.steps[-1].update(meta=meta, output=out)
    db.update("incidents", inc["id"], {"steps": run.steps})
    fb = fallback_text(inc["kind"], facts, action)
    if not out or not isinstance(out.get("root_cause"), str):
        run.step("guard", "LLM output unusable - using evidence template", detail=meta.get("error", "invalid JSON"))
        return {**fb, "confidence": facts.get("evidence_confidence", 0.5), "llm_ok": 0, "model": meta["model"]}
    hard, soft = grounding_problems(inc["kind"], facts, action, out["root_cause"])
    if hard:
        run.step("guard", "Grounding check failed - LLM output discarded, evidence template used",
                 detail="; ".join(hard), rejected=out["root_cause"])
        return {**fb, "confidence": facts.get("evidence_confidence", 0.5), "llm_ok": 0, "model": meta["model"]}
    root = out["root_cause"][:400]
    if soft:
        run.step("guard", "Grounding check: root cause too vague - sharpened from evidence, LLM summary kept",
                 detail="; ".join(soft), rejected=root)
        root = fb["root_cause"]
    else:
        run.step("guard", "Grounding check passed", detail="root cause names the evidenced component/version")
    rb = out.get("runbook") if isinstance(out.get("runbook"), list) and len(out["runbook"]) >= 2 else fb["runbook"]
    try:
        c = float(out.get("confidence", 0.6))
    except (TypeError, ValueError):
        c = 0.6
    conf = round((min(max(c, 0), 1) + facts.get("evidence_confidence", 0.5)) / 2, 2)
    return {"root_cause": root, "summary": str(out.get("summary") or root)[:900],
            "runbook": [str(x)[:200] for x in rb][:6], "confidence": conf, "llm_ok": 1, "model": meta["model"]}


async def pick_skill(inc: dict, run: Run) -> tuple[str, str]:
    rule = rule_skill(inc["kind"])
    lst = "\n".join(f'- "{k}": {s["description"]}' for k, s in SKILLS.items())
    run.step("llm", "Incident classification & skill selection")
    out, meta = await llm.chat_json(
        "You are an SRE triage agent. Choose the single best investigation skill. Reply with JSON only.",
        f"Alert: {inc['title']} (signal type: {inc['kind']}, entity: {inc['entity']})\nSkills:\n{lst}\n"
        'Reply: {"skill": "<one id from the list>", "reason": "<max 12 words>"}', max_tokens=50, timeout=120)
    run.steps[-1].update(meta=meta, output=out)
    choice = (out or {}).get("skill")
    if choice in SKILLS:
        reason = str(out.get("reason", ""))[:300]
        if choice != rule:
            # A tiny model can mis-route; the signal type is ground truth for which tools apply.
            return rule, f"LLM suggested {choice} ({reason}); overridden by signal-type rule -> {rule}"
        return choice, reason or "selected by LLM"
    return rule, "LLM unavailable/invalid - rule-based selection by signal type"


async def analyze(inc_id: int):
    async with _sem:
        inc = db.one("SELECT * FROM incidents WHERE id=?", (inc_id,))
        if not inc:
            return
        t0 = time.time()
        db.update("incidents", inc_id, {"status": "analyzing"})
        run = Run(inc_id)
        run.step("info", "Agentic AI orchestrator started", detail=f"signal={inc['kind']} entity={inc['entity']}")
        skill, reason = await pick_skill(inc, run)
        sk = SKILLS[skill]
        run.step("skill", f"Skill selected: {sk['name']} ({sk['category']})", detail=reason, tools=sk["tools"])
        db.update("incidents", inc_id, {"skill": skill, "skill_reason": reason})

        facts, cands = await PLAYBOOKS[skill](run, {**inc["signal"], "incident_id": inc_id})
        for c in cands:
            c["label"] = remediation.label(c)
        run.step("analysis", "Evidence correlated", facts=facts, candidates=cands)

        # Dry run every candidate - read-only. Safe ones first; nothing is applied here.
        try:
            edges = (await servicemap.build()).get("edges", [])
        except Exception:
            edges = []
        for c in cands:
            c["dry_run"] = await remediation.dry_run(c, edges)
            dr = c["dry_run"]
            run.step("dryrun", f"Dry run: {c['label']}", ok=dr["ok"], checks=dr["checks"], changes=dr["changes"],
                     impact=dr["impact"])
        cands.sort(key=lambda c: not c["dry_run"]["ok"])
        if not cands[0]["dry_run"]["ok"]:
            cands.insert(0, {"type": "manual", "params": {}, "label": remediation.label({"type": "manual"}),
                             "dry_run": await remediation.dry_run({"type": "manual", "params": {}})})
            run.step("dryrun", "No candidate passed its dry run - recommending manual investigation", ok=False)
        action = cands[0]
        p = action.get("params", {})
        owner = remediation.owner_of(p.get("service") or (inc["entity"] if inc["entity_type"] == "service" else None),
                                     inc["entity"] if inc["entity_type"] == "host" else None, inc["kind"])

        sig = signature(inc["kind"], facts, action)
        rb = db.one("SELECT * FROM runbooks WHERE signature=? AND enabled=1", (sig,))
        if rb:
            run.step("memory", f"Runbook found in incident memory: RB-{rb['id']} '{rb['title']}'",
                     detail=f"used {rb['uses']}x, avg score {round(rb['score_sum'] / rb['score_n'], 1) if rb['score_n'] else '-'}"
                            " - skipping new RCA generation, reusing approved runbook")
            fb = fallback_text(inc["kind"], facts, action)
            res = {"root_cause": fb["root_cause"],
                   "summary": f"Matches known incident pattern RB-{rb['id']} (first seen in P-{rb['source_incident']}). "
                              + fb["summary"],
                   "runbook": rb["runbook"] if isinstance(rb["runbook"], list) else json.loads(rb["runbook"]),
                   "confidence": round(min(0.97, facts.get("evidence_confidence", 0.6) + 0.15), 2), "llm_ok": 0,
                   "model": "runbook-memory"}
            db.ex("UPDATE runbooks SET uses=uses+1, updated_at=? WHERE id=?", (time.time(), rb["id"]))
            path = "known"
        else:
            run.step("memory", "No matching runbook - new incident, generating RCA & recommendation", detail=sig)
            res = await summarize(inc, skill, facts, action, run)
            path = "new"

        origin = action["params"].get("service") or inc["entity"]
        title = f"{KIND_LABEL.get(inc['kind'], inc['kind'])} - root cause in {origin}" if origin != inc["entity"] \
            else inc["title"]
        run.step("done", f"RCA + dry-run plan ready - waiting for approval from owner {owner}", detail=action["label"])
        db.update("incidents", inc_id, {
            "owner": owner, "dry_run": action["dry_run"], "evidence": findings(inc["kind"], facts),
            "status": "awaiting_approval", "analyzed_at": time.time(), "title": title, "path": path,
            "root_cause": res["root_cause"], "summary": res["summary"], "confidence": res["confidence"],
            "runbook": res["runbook"], "facts": facts, "action": action, "candidates": cands,
            "runbook_id": rb["id"] if rb else None, "llm_model": res["model"], "llm_ok": res["llm_ok"],
            "analysis_ms": int((time.time() - t0) * 1000), "steps": run.steps})
        await notify.send(db.one("SELECT * FROM incidents WHERE id=?", (inc_id,)), "rca_ready")
