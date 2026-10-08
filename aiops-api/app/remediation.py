"""Allow-listed corrective actions.

Every action has two halves:
  dry_run(action)  - read-only: checks preconditions, computes the exact change and its blast radius.
                     Runs automatically when the agent proposes the action, and again right before execution.
  execute(action)  - the real change. Only reachable from the owner-approval endpoint, and only if the
                     pre-flight dry run still passes.
"""
import asyncio
import ipaddress
import os
import re
import time

import httpx

from . import db, repo
from . import telemetry as tm

EDGE_DIR = os.environ.get("EDGE_DIR", "/edge")
BLOCKLIST = os.path.join(EDGE_DIR, "blocklist.conf")
FW_CONTAINER = "edge-fw"
INTERNAL_NETS = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8")]

ACTIONS = {
    "rollback_deployment": "Roll back {service} to v{to_version} ({to_commit})",
    "restart_service": "Restart {service} (all instances, rolling)",
    "restart_instance": "Restart instance {instance} of {service}",
    "block_ip": "Block source IP {ip} at the edge firewall",
    "manual": "No automated action - manual investigation",
}


def label(action: dict) -> str:
    try:
        return ACTIONS[action["type"]].format(**action.get("params", {}))
    except Exception:
        return action.get("type", "?")


def app_row(service: str) -> dict | None:
    return repo.service(service)


def admin_urls(service: str) -> list[str]:
    return repo.admin_urls(service)


def admin_url(service: str) -> str | None:  # "is this service controllable at runtime?"
    urls = admin_urls(service)
    return urls[0] if urls else None


def containers_of(service: str) -> list[str]:
    return repo.containers_of(service)


def owner_of(service: str | None = None, host: str | None = None, kind: str = "") -> str:
    if kind == "auth_bruteforce":
        r = repo.service("edge-firewall")
        return (r or {}).get("owner") or "team-security"
    if service:
        r = repo.service(service)
        if r:
            return r.get("owner") or "unassigned"
    if host:
        h = repo.host(host)
        return (h or {}).get("owner") or "team-platform"
    return "unassigned"


async def set_app_state(service: str, state: dict) -> list[dict]:
    urls = admin_urls(service)
    if not urls:
        raise RuntimeError(f"{service} has no admin endpoint registered")
    out = []
    async with httpx.AsyncClient(timeout=10) as c:
        for u in urls:
            r = await c.post(f"{u}/admin/state", json=state)
            r.raise_for_status()
            out.append(r.json())
    return out


async def _get_states(service: str) -> list[dict]:
    out = []
    async with httpx.AsyncClient(timeout=5) as c:
        for u in admin_urls(service):
            try:
                out.append({"url": u, **(await c.get(f"{u}/admin/state")).json()})
            except Exception as e:
                out.append({"url": u, "error": str(e)})
    return out


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


async def _version_history(service: str, version: str, commit: str) -> tuple[float | None, float]:
    sel = f'service_name="{service}",{tm.SRV},app_version="{version}",app_commit="{commit}"'
    tot = await tm.prom_value(f"sum(increase({tm.CALLS}{{{sel}}}[24h]))")
    err = await tm.prom_value(f'sum(increase({tm.CALLS}{{{sel},status_code="STATUS_CODE_ERROR"}}[24h])) or vector(0)')
    if not tot:
        return None, 0.0
    return (err or 0) / tot, tot


async def last_known_good(service: str, bad_versions: set[tuple[str, str]]) -> tuple[dict | None, list[dict]]:
    """Walk deploy history newest-first; return the first build that is not failing now AND whose own
    traffic over the last 24 h was healthy. A deploy record alone is not proof (a rollback can be wrong)."""
    seen, considered = set(), []
    thr = db.fsetting("err_threshold")
    for d in repo.deployments(service, limit=200):
        key = (d["version"], d["commit_hash"])
        if key in seen:
            continue
        seen.add(key)
        if key in bad_versions:
            considered.append({"build": f"v{key[0]} ({key[1]})", "verdict": "failing now"})
            continue
        er, calls = await _version_history(service, *key)
        if er is not None and er < thr:
            considered.append({"build": f"v{key[0]} ({key[1]})", "verdict": f"known-good, {er * 100:.2f}% over {int(calls)} req"})
            return d, considered
        considered.append({"build": f"v{key[0]} ({key[1]})",
                           "verdict": "no traffic in 24 h" if er is None else f"{er * 100:.1f}% failures - rejected"})
        if len(considered) >= 8:
            break
    return None, considered


def callers_of(service: str, edges: list[dict]) -> list[str]:
    return sorted({e["from"] for e in edges if e["to"] == service})


# ---------------- dry run ----------------
async def dry_run(action: dict, edges: list[dict] | None = None) -> dict:
    t, p = action["type"], action.get("params", {})
    checks, changes, impact = [], [], ""
    edges = edges or []
    try:
        if t == "rollback_deployment":
            svc = p["service"]
            states = await _get_states(svc)
            reach = [s for s in states if "error" not in s]
            checks.append(_check("admin endpoint reachable", reach and len(reach) == len(states),
                                 f"{len(reach)}/{len(states)} instances answered /admin/state"))
            checks.append(_check("target differs from failing build",
                                 (p["to_version"], p["to_commit"]) != (p.get("from_version"), p.get("from_commit")),
                                 f"v{p.get('from_version')} ({p.get('from_commit')}) -> v{p['to_version']} ({p['to_commit']})"))
            er, calls = await _version_history(svc, p["to_version"], p["to_commit"])
            thr = db.fsetting("err_threshold")
            checks.append(_check("target is known-good", er is not None and er < thr,
                                 f"v{p['to_version']} ({p['to_commit']}) served {int(calls)} requests in the last 24 h "
                                 f"with {er * 100:.2f}% failures" if er is not None
                                 else "no traffic recorded for the target build in the last 24 h"))
            for s in reach:
                changes.append(f"{s['url']}: version {s.get('version')} ({s.get('commit')}) -> {p['to_version']} ({p['to_commit']})")
            cs = callers_of(svc, edges)
            impact = (f"Runtime switch on {len(reach)} instance(s), no container restart. "
                      f"Callers that recover: {', '.join(cs) or 'none seen'}.")
        elif t in ("restart_service", "restart_instance"):
            svc = p["service"]
            targets = [p["instance"]] if t == "restart_instance" else containers_of(svc)
            all_inst = containers_of(svc)
            for name in targets:
                info = await tm.container_info(name)
                checks.append(_check(f"container {name} exists", info is not None,
                                     f"status={info['status']}, restarts so far={info['restart_count']}" if info else "not found"))
            others = [c for c in all_inst if c not in targets]
            healthy_others = []
            for c in others:
                info = await tm.container_info(c)
                if info and info["status"] == "running":
                    healthy_others.append(c)
            if t == "restart_instance":
                checks.append(_check("other replicas can take the traffic", bool(healthy_others),
                                     f"still serving: {', '.join(healthy_others) or 'none'}"))
                impact = (f"LB keeps routing to {', '.join(healthy_others)}; requests in flight on {targets[0]} may fail "
                          f"(~5 s).")
            else:
                impact = (f"Rolling restart of {len(targets)} instance(s), one at a time. "
                          + ("Single instance: callers " + (", ".join(callers_of(svc, edges)) or "-")
                             + " see ~5 s of errors." if len(targets) == 1 else "At least one instance stays up."))
            changes += [f"docker restart {n}" for n in targets]
        elif t == "block_ip":
            ip = p["ip"]
            try:
                addr = ipaddress.ip_address(ip)
                valid, internal = True, any(addr in n for n in INTERNAL_NETS)
            except ValueError:
                valid, internal = False, False
            checks.append(_check("valid IP address", valid, ip))
            checks.append(_check("not an internal / corporate address", valid and not internal,
                                 "internal ranges are never auto-blocked" if internal else "external address"))
            current = open(BLOCKLIST).read() if os.path.exists(BLOCKLIST) else ""
            already = re.search(rf"^{re.escape(ip)}\s", current, re.M) is not None
            checks.append(_check("not already blocked", not already, "already in blocklist" if already else "new entry"))
            logs = await tm.edge_logs("edge-firewall", minutes=5, line_filter=f'|= "{ip}"')
            ok_logins = [l for l in logs if l.get("path") == "/api/login" and l.get("status") == 200]
            checks.append(_check("no legitimate traffic from this IP", not ok_logins,
                                 f"{len(logs)} requests in 5 min, {len(ok_logins)} successful logins"))
            candidate = current.rstrip("\n") + f"\n{ip} 1;  # P-{p.get('incident', '?')} {time.strftime('%Y-%m-%d %H:%M')}\n"
            staged = os.path.join(EDGE_DIR, "blocklist.dryrun.conf")
            with open(staged, "w") as f:
                f.write(candidate)
            main = open(os.path.join(EDGE_DIR, "fw.conf")).read().replace("/etc/nginx/edge/blocklist.conf",
                                                                           "/etc/nginx/edge/blocklist.dryrun.conf")
            with open(os.path.join(EDGE_DIR, "fw.dryrun.conf"), "w") as f:
                f.write(main)
            code, out = await tm.container_exec(FW_CONTAINER, ["nginx", "-t", "-c", "/etc/nginx/edge/fw.dryrun.conf"])
            checks.append(_check("firewall config validates (nginx -t)", code == 0, out.strip().splitlines()[-1] if out else ""))
            changes.append(f"+ {ip} 1;   (edge/blocklist.conf)")
            changes.append("nginx -s reload on edge-fw")
            impact = f"Drops {len(logs)} req / 5 min from {ip}. Nothing else changes."
        else:
            checks.append(_check("no automated change", True, "engineer follows the runbook manually"))
            impact = "None - read-only."
    except Exception as e:
        checks.append(_check("dry run completed", False, f"{type(e).__name__}: {e}"))
    return {"ts": time.time(), "ok": all(c["ok"] for c in checks), "checks": checks, "changes": changes,
            "impact": impact}


# ---------------- execute (owner-approved only) ----------------
async def execute(action: dict, incident_id: int, approver: str) -> dict:
    t, p = action["type"], action.get("params", {})
    if t == "rollback_deployment":
        await set_app_state(p["service"], {"version": p["to_version"], "commit": p["to_commit"], "profile": "healthy",
                                           "error_rate": 0, "error_msg": "", "latency_ms": 0})
        repo.add_deployment(p["service"], p["to_version"], p["to_commit"], author=f"aiops-bot (approved by {approver})",
                            message=f"rollback by AIOps for P-{incident_id}", profile="healthy")
        return {"ok": True, "detail": f"{p['service']} now running v{p['to_version']} ({p['to_commit']})"}
    if t in ("restart_service", "restart_instance"):
        names = [p["instance"]] if t == "restart_instance" else containers_of(p["service"])
        for n in names:
            await asyncio.to_thread(lambda n=n: tm.docker_client().containers.get(n).restart(timeout=5))
            if len(names) > 1:
                await asyncio.sleep(8)  # rolling: let the instance come back before the next one
        return {"ok": True, "detail": f"restarted {', '.join(names)}"}
    if t == "block_ip":
        with open(os.path.join(EDGE_DIR, "blocklist.dryrun.conf")) as f:
            staged = f.read()
        if p["ip"] not in staged:
            raise RuntimeError("staged config does not contain the approved IP - re-run dry run")
        with open(BLOCKLIST, "w") as f:
            f.write(staged)
        code, out = await tm.container_exec(FW_CONTAINER, ["nginx", "-s", "reload"])
        if code != 0:
            raise RuntimeError(f"nginx reload failed: {out}")
        return {"ok": True, "detail": f"{p['ip']} blocked at edge-fw (config reloaded)"}
    return {"ok": True, "detail": "manual action - nothing executed"}
