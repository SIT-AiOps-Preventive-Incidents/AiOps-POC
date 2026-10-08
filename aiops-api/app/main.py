import asyncio
import json
import os
import random
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, db, detector, llm, notify, remediation, servicemap
from . import telemetry as tm

TARGETS_DIR = os.environ.get("TARGETS_DIR", "/targets")
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3001")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8080")
STATIC = os.path.join(os.path.dirname(__file__), "static")
AGENT_DIST = os.path.join(os.path.dirname(__file__), "agent_dist")
OTLP_PUBLIC = os.environ.get("OTLP_PUBLIC_URL") or PUBLIC_URL.rsplit(":", 1)[0] + ":4318"

DEMO_APPS = [
    ("Shop Frontend", "frontend", "web gateway", "team-web", "9f3c2e1"),
    ("Checkout Service", "checkout", "orders", "team-orders", "4b7d0a9"),
    ("Payment Service", "payment", "payments", "team-payments", "c81e5f2"),
    ("Inventory Service", "inventory", "catalog", "team-catalog", "e2a94d7"),
]


def write_targets():
    hosts = db.q("SELECT * FROM hosts")
    data = [{"targets": [h["address"]], "labels": {"host": h["name"], "environment": h["environment"] or "",
                                                     **(h["labels"] or {})}} for h in hosts]
    os.makedirs(TARGETS_DIR, exist_ok=True)
    tmp = os.path.join(TARGETS_DIR, ".infra.json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, os.path.join(TARGETS_DIR, "infra.json"))


def seed():
    if not db.one("SELECT id FROM apps LIMIT 1"):
        for name, svc, _, team, commit in DEMO_APPS:
            db.insert("apps", {"name": name, "service_name": svc, "language": "python", "team": team,
                               "repo": f"gitlab.sit.kmutt.ac.th/shop/{svc}", "environment": "poc", "container": svc,
                               "admin_url": f"http://{svc}:8000", "created_at": time.time()})
            db.insert("deployments", {"service": svc, "version": "1.2.0", "commit_hash": commit, "author": "ci-pipeline",
                                      "message": "release 1.2.0", "profile": "healthy",
                                      "ts": time.time() - random.randint(3, 20) * 3600})
    if not db.one("SELECT id FROM hosts LIMIT 1"):
        db.insert("hosts", {"name": "cp26pt1", "address": "node-exporter:9100", "os": "Ubuntu 26.04",
                            "environment": "poc", "labels": {"role": "docker-host"}, "created_at": time.time()})
    # v2 topology: firewall -> LB -> frontend-a/b. Idempotent so existing databases are upgraded in place.
    db.ex("UPDATE apps SET container='frontend-a,frontend-b', admin_url='http://frontend-a:8000,http://frontend-b:8000' "
          "WHERE service_name='frontend' AND container='frontend'")
    for svc, name, cont, owner in (("edge-firewall", "Edge Firewall", "edge-fw", "team-network"),
                                   ("edge-lb", "Edge Load Balancer", "edge-lb", "team-network")):
        if not db.one("SELECT id FROM apps WHERE service_name=?", (svc,)):
            db.insert("apps", {"name": name, "service_name": svc, "language": "nginx", "team": owner, "owner": owner,
                               "repo": "infra/edge", "environment": "poc", "container": cont, "admin_url": "",
                               "kind": "network", "created_at": time.time()})
    db.ex("UPDATE apps SET owner=team WHERE owner IS NULL OR owner=''")
    db.ex("UPDATE apps SET kind='service' WHERE kind IS NULL")
    db.ex("UPDATE hosts SET owner='team-platform' WHERE owner IS NULL OR owner=''")
    write_targets()


async def rotate_edge_logs():
    """Network device logs are shipped to Loki; keep the local files from filling the disk."""
    while True:
        for f in ("/var/log/edge/firewall.log", "/var/log/edge/lb.log"):
            try:
                if os.path.getsize(f) > 50 * 2**20:
                    open(f, "w").close()
            except OSError:
                pass
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(_):
    db.conn()
    seed()
    tasks = [asyncio.create_task(detector.loop()), asyncio.create_task(rotate_edge_logs())]
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="AIOps One Solution", lifespan=lifespan)


# ---------------- overview ----------------
async def service_health(svc: str) -> dict:
    rps, err, p95 = await asyncio.gather(tm.prom_value(tm.svc_expr(svc, "rps")),
                                         tm.prom_value(tm.svc_expr(svc, "error_rate")),
                                         tm.prom_value(tm.svc_expr(svc, "p95")))
    open_inc = db.one("SELECT id FROM incidents WHERE (entity=? OR json_extract(action,'$.params.service')=?) "
                      "AND status NOT IN ('resolved','rejected','closed') LIMIT 1", (svc, svc))
    dep = db.one("SELECT version, commit_hash, ts FROM deployments WHERE service=? ORDER BY ts DESC LIMIT 1", (svc,))
    status = "no-data" if rps is None else ("problem" if open_inc else "healthy")
    return {"service": svc, "rps": rps, "error_rate": err, "p95_ms": p95, "status": status,
            "problem_id": open_inc and open_inc["id"], "version": dep and dep["version"],
            "commit": dep and dep["commit_hash"], "deployed_at": dep and dep["ts"]}


async def host_health(h: dict) -> dict:
    vals = await asyncio.gather(*(tm.prom_value(tm.host_expr(h["name"], m)) for m in ("up", "cpu", "mem", "disk", "load")))
    up, cpu, mem, disk, load = vals
    open_inc = db.one("SELECT id FROM incidents WHERE entity=? AND entity_type='host' "
                      "AND status NOT IN ('resolved','rejected','closed') LIMIT 1", (h["name"],))
    if up is None or (up == 0 and h.get("kind") == "workstation"):
        status = "offline" if h.get("agent") == "aiops-agent" else "no-data"
    else:
        status = "down" if up == 0 else ("problem" if open_inc else "healthy")
    return {**h, "up": up, "cpu": cpu, "mem": mem, "disk": disk, "load": load, "status": status,
            "problem_id": open_inc and open_inc["id"]}


@app.get("/api/overview")
async def overview():
    apps = db.q("SELECT * FROM apps ORDER BY id")
    hosts = db.q("SELECT * FROM hosts ORDER BY id")
    svcs = [{**h, "name": a["name"], "language": a.get("language"), "kind": a.get("kind")}
            for a, h in zip(apps, await asyncio.gather(*(service_health(a["service_name"]) for a in apps)))]
    hs = await asyncio.gather(*(host_health(h) for h in hosts))
    incs = db.q("SELECT * FROM incidents ORDER BY id DESC")
    open_ = [i for i in incs if i["status"] not in ("resolved", "rejected", "closed")]
    mttd = [i["detected_at"] - i["started_at"] for i in incs if i["started_at"]]
    mtta = [i["analyzed_at"] - i["detected_at"] for i in incs if i["analyzed_at"]]
    mttr = [i["resolved_at"] - i["detected_at"] for i in incs if i["resolved_at"]]
    scores = [i["score"] for i in incs if i["score"]]
    avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None  # noqa: E731
    return {"services": svcs, "hosts": hs, "open_problems": open_[:10],
            "kpi": {"open": len(open_), "total": len(incs), "mttd_s": avg(mttd), "mtta_s": avg(mtta),
                    "mttr_s": avg(mttr), "avg_score": avg(scores),
                    "awaiting_approval": sum(1 for i in open_ if i["status"] == "awaiting_approval")},
            "detector": detector.LAST_RUN, "llm": await llm.status(), "grafana_url": GRAFANA_URL}


# ---------------- services / connect app ----------------
class AppIn(BaseModel):
    name: str = ""
    service_name: str
    language: str = "python"
    team: str = ""
    owner: str = ""
    repo: str = ""
    environment: str = "production"
    container: str = ""
    admin_url: str = ""


@app.get("/api/apps")
async def list_apps():
    apps = db.q("SELECT * FROM apps ORDER BY id")
    health = await asyncio.gather(*(service_health(a["service_name"]) for a in apps))
    return [{**a, **h} for a, h in zip(apps, health)]


@app.post("/api/apps")
async def create_app(body: AppIn):
    if db.one("SELECT id FROM apps WHERE service_name=?", (body.service_name,)):
        raise HTTPException(409, "service_name already connected")
    data = body.model_dump()
    data["service_name"] = data["service_name"].strip()
    data["name"] = data["name"] or data["service_name"].replace("-", " ").replace("_", " ").title()
    data["team"] = data["team"] or data["owner"]
    data["owner"] = data["owner"] or data["team"] or "unassigned"
    rid = db.insert("apps", {**data, "kind": "service", "created_at": time.time()})
    return db.one("SELECT * FROM apps WHERE id=?", (rid,))


@app.delete("/api/apps/{aid}")
async def delete_app(aid: int):
    db.ex("DELETE FROM apps WHERE id=?", (aid,))
    return {"ok": True}


@app.get("/api/apps/{svc}/verify")
async def verify_app(svc: str):
    rps = await tm.prom_value(tm.svc_expr(svc, "rps", "5m"))
    logs = await tm.loki_count(f'sum(count_over_time({{service_name="{svc}"}}[5m]))')
    traces = await tm.tempo_search(f'{{ resource.service.name = "{svc}" }}', minutes=5, limit=1)
    return {"metrics": rps is not None and rps > 0, "logs": logs > 0, "traces": bool(traces),
            "rps": rps, "log_lines_5m": logs}


@app.get("/api/services/{svc}")
async def service_detail(svc: str):
    a = db.one("SELECT * FROM apps WHERE service_name=?", (svc,))
    if not a:
        raise HTTPException(404)
    series = {}
    for m in ("rps", "error_rate", "p95"):
        r = await tm.prom_range(tm.svc_expr(svc, m), minutes=60, step=30)
        series[m] = r[0]["points"] if r else []
    sel = f'service_name="{svc}",{tm.SRV}'
    eps = await tm.prom(f"sum by (span_name) (rate({tm.CALLS}{{{sel}}}[5m]))")
    eperr = await tm.prom(f'sum by (span_name) (rate({tm.CALLS}{{{sel},status_code="STATUS_CODE_ERROR"}}[5m]))')
    emap = {e["metric"].get("span_name"): float(e["value"][1]) for e in eperr}
    endpoints = [{"name": e["metric"].get("span_name"), "rps": round(float(e["value"][1]), 3),
                  "error_rate": round(emap.get(e["metric"].get("span_name"), 0) / float(e["value"][1]), 4)
                  if float(e["value"][1]) else 0} for e in eps]
    calls = await tm.prom(f'sum by (service_name) (rate({tm.CALLS}{{span_kind="SPAN_KIND_CLIENT",service_name="{svc}"}}[5m]))')
    logs = await tm.loki_logs(f'{{service_name="{svc}"}}', minutes=15, limit=40)
    traces = await tm.tempo_search(f'{{ resource.service.name = "{svc}" }}', minutes=15, limit=15)
    return {"app": a, "health": await service_health(svc), "series": series, "endpoints": endpoints,
            "versions": await tm.error_rate_by_version(svc, "5m"),
            "deployments": db.q("SELECT * FROM deployments WHERE service=? ORDER BY ts DESC LIMIT 15", (svc,)),
            "logs": logs, "traces": traces, "outbound_rps": calls[0]["value"][1] if calls else None,
            "incidents": db.q("SELECT id,title,status,severity,detected_at FROM incidents WHERE entity=? "
                              "OR json_extract(action,'$.params.service')=? ORDER BY id DESC LIMIT 10", (svc, svc))}


@app.get("/api/servicemap")
async def get_servicemap():
    return await servicemap.build()


@app.get("/api/topology")
async def topology():
    """Service flow from client-span parent/child pairs is not in spanmetrics, so derive from recent traces."""
    traces = await tm.tempo_search("{ }", minutes=5, limit=15)
    edges = {}
    for t in traces[:8]:
        spans = await tm.tempo_trace(t["traceID"])
        by_id = {s["id"]: s for s in spans}
        for s in spans:
            p = by_id.get(s["parent"])
            if p and p["service"] != s["service"]:
                k = (p["service"], s["service"])
                edges[k] = edges.get(k, 0) + 1
    return [{"from": a, "to": b, "count": c} for (a, b), c in edges.items()]


@app.get("/api/traces/{tid}")
async def get_trace(tid: str):
    return await tm.tempo_trace(tid)


# ---------------- infrastructure / connect infra ----------------
class HostIn(BaseModel):
    name: str
    address: str
    os: str = "Linux"
    environment: str = "production"
    labels: dict = {}


@app.get("/api/hosts")
async def list_hosts():
    hosts = db.q("SELECT * FROM hosts ORDER BY id")
    return await asyncio.gather(*(host_health(h) for h in hosts))


@app.post("/api/hosts")
async def create_host(body: HostIn):
    if db.one("SELECT id FROM hosts WHERE name=?", (body.name,)):
        raise HTTPException(409, "host name already connected")
    rid = db.insert("hosts", {**body.model_dump(), "created_at": time.time()})
    write_targets()
    return db.one("SELECT * FROM hosts WHERE id=?", (rid,))


class RegisterIn(BaseModel):
    name: str
    os: str = ""
    arch: str = ""
    kind: str = "server"


@app.post("/api/hosts/register")
async def register_host(body: RegisterIn):
    """Called by the agent installer. Idempotent: re-running the installer keeps the same host."""
    h = db.one("SELECT id FROM hosts WHERE name=?", (body.name,))
    data = {"address": "push (aiops-agent)", "os": f"{body.os} {body.arch}".strip(), "agent": "aiops-agent",
            "kind": body.kind if body.kind in ("server", "workstation") else "server"}
    if h:
        db.update("hosts", h["id"], data)
    else:
        db.insert("hosts", {"name": body.name, "environment": "poc", "labels": {"role": data["kind"]},
                            "owner": "team-platform", "created_at": time.time(), **data})
    return db.one("SELECT * FROM hosts WHERE name=?", (body.name,))


@app.get("/api/discover")
async def discover():
    """Telemetry that is arriving but not connected yet - one tap to add it."""
    known = {a["service_name"] for a in db.q("SELECT service_name FROM apps")}
    seen = {}
    for r in await tm.prom(f'sum by (service_name) (rate({tm.CALLS}{{span_kind="SPAN_KIND_SERVER"}}[15m]))'):
        n = r["metric"].get("service_name")
        if n:
            seen[n] = round(float(r["value"][1]), 3)
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            vals = (await c.get(f"{tm.LOKI}/loki/api/v1/label/service_name/values",
                                params={"start": int((time.time() - 900) * 1e9)})).json().get("data", [])
        for n in vals:
            seen.setdefault(n, None)
    except Exception:
        pass
    services = [{"service_name": n, "rps": r} for n, r in sorted(seen.items())
                if n not in known and n not in ("aiops-agent", "unknown_service")]
    hosts_known = {h["name"] for h in db.q("SELECT name FROM hosts")}
    hosts = [r["metric"].get("host_name") for r in await tm.prom("max by (host_name) (aiops_host_up)")]
    return {"services": services, "hosts": [h for h in hosts if h and h not in hosts_known],
            "otlp_endpoint": OTLP_PUBLIC, "api": PUBLIC_URL}


@app.get("/api/ping")
async def ping():
    return {"ok": True}


def _dist(name: str) -> str:
    with open(os.path.join(AGENT_DIST, name)) as f:
        return f.read().replace("__API__", PUBLIC_URL).replace("__OTLP__", OTLP_PUBLIC)


@app.get("/install/agent.sh", response_class=PlainTextResponse)
async def install_script():
    return _dist("install.sh")


@app.get("/install/uninstall.sh", response_class=PlainTextResponse)
async def uninstall_script():
    return _dist("uninstall.sh")


@app.get("/install/aiops-agent.py", response_class=PlainTextResponse)
async def agent_py():
    return _dist("aiops-agent.py")


@app.delete("/api/hosts/{hid}")
async def delete_host(hid: int):
    db.ex("DELETE FROM hosts WHERE id=?", (hid,))
    write_targets()
    return {"ok": True}


@app.get("/api/hosts/{name}")
async def host_detail(name: str):
    h = db.one("SELECT * FROM hosts WHERE name=?", (name,))
    if not h:
        raise HTTPException(404)
    series = {}
    for m in ("cpu", "mem", "disk", "load"):
        r = await tm.prom_range(tm.host_expr(name, m), minutes=60, step=30)
        series[m] = r[0]["points"] if r else []
    is_local = h["address"].startswith("node-exporter")
    procs = []
    if h.get("agent") == "aiops-agent":
        procs = (await agent.t_getTopProcesses(name)).get("processes", [])
    return {"host": await host_health(h), "series": series, "processes": procs,
            "containers": await tm.containers(with_stats=True) if is_local else [],
            "incidents": db.q("SELECT id,title,status,severity,detected_at FROM incidents WHERE entity=? "
                              "ORDER BY id DESC LIMIT 10", (name,))}


# ---------------- deployments (CI/CD hook) ----------------
class DeployIn(BaseModel):
    service: str
    version: str
    commit: str
    author: str = "ci-pipeline"
    message: str = ""
    profile: str | None = None


BAD_PROFILES = {
    "payment": {"error_rate": 0.45,
                "error_msg": "TypeError: 'NoneType' object is not subscriptable at discount.py:42 in apply_member_discount()"},
    "inventory": {"error_rate": 0.4, "error_msg": "KeyError: 'warehouse_id' at stock.py:88 in reserve_items()"},
    "checkout": {"error_rate": 0.4, "error_msg": "ValueError: invalid shipping zone 'TH-99' at shipping.py:17"},
    "frontend": {"error_rate": 0.3, "error_msg": "TemplateError: undefined variable 'promo_banner'"},
}


@app.post("/api/deployments")
async def record_deploy(body: DeployIn):
    """Called from CI after a deploy (version + commit hash). Demo apps also get the version applied at runtime."""
    rid = db.insert("deployments", {"service": body.service, "version": body.version, "commit_hash": body.commit,
                                    "author": body.author, "message": body.message,
                                    "profile": body.profile or "healthy", "ts": time.time()})
    if remediation.admin_urls(body.service):
        state = {"version": body.version, "commit": body.commit, "profile": body.profile or "healthy",
                 "error_rate": 0, "error_msg": ""}
        if body.profile == "bad":
            state.update(BAD_PROFILES.get(body.service, BAD_PROFILES["payment"]))
        try:
            await remediation.set_app_state(body.service, state)
        except Exception as e:
            return {"id": rid, "warning": f"recorded, but could not reach app admin: {e}"}
    return {"id": rid}


@app.get("/api/deployments")
async def deployments():
    return db.q("SELECT * FROM deployments ORDER BY ts DESC LIMIT 100")


# ---------------- problems / incidents ----------------
@app.get("/api/incidents")
async def incidents(status: str | None = None):
    rows = db.q("SELECT id,title,kind,entity_type,entity,severity,status,started_at,detected_at,analyzed_at,"
                "resolved_at,skill,path,root_cause,confidence,score,signal,action,owner FROM incidents "
                "ORDER BY id DESC LIMIT 200")
    if status == "open":
        rows = [r for r in rows if r["status"] not in ("resolved", "rejected", "closed")]
    return rows


@app.get("/api/incidents/{iid}")
async def incident(iid: int):
    inc = db.one("SELECT * FROM incidents WHERE id=?", (iid,))
    if not inc:
        raise HTTPException(404)
    inc["notifications"] = db.q("SELECT id,ts,event,status FROM notifications WHERE incident_id=? ORDER BY id", (iid,))
    inc["grafana_url"] = GRAFANA_URL
    return inc


class Approval(BaseModel):
    approver: str = "on-call engineer"
    action_index: int = 0
    comment: str = ""
    owner_confirmed: bool = False


async def _verify(iid: int):
    await asyncio.sleep(db.fsetting("verify_after_s"))
    inc = db.one("SELECT * FROM incidents WHERE id=?", (iid,))
    # The 1-minute rate window still holds errors from just before/while the fix applied - give it a few
    # more chances to come back clean before calling the remediation a failure.
    checks = []
    for attempt in range(5):
        ok = await detector.is_healthy(inc)
        checks.append({"ts": time.time(), "healthy": ok})
        if ok:
            break
        await asyncio.sleep(20)
    ex = inc["execution"] or {}
    ex["verification"] = {"ts": time.time(), "healthy": ok, "attempts": len(checks)}
    if ok:
        db.update("incidents", iid, {"status": "resolved", "resolved_at": time.time(), "execution": ex})
        detector.clear(inc["kind"], inc["entity"])
        await notify.send(db.one("SELECT * FROM incidents WHERE id=?", (iid,)), "resolved")
    else:
        db.update("incidents", iid, {"status": "remediation_failed", "execution": ex})
        await notify.send(db.one("SELECT * FROM incidents WHERE id=?", (iid,)), "remediation_failed")


@app.post("/api/incidents/{iid}/approve")
async def approve(iid: int, body: Approval):
    inc = db.one("SELECT * FROM incidents WHERE id=?", (iid,))
    if not inc or inc["status"] not in ("awaiting_approval", "remediation_failed"):
        raise HTTPException(409, "incident is not waiting for approval")
    if not body.owner_confirmed:
        raise HTTPException(403, f"approval must come from the owner ({inc['owner'] or 'unassigned'})")
    cands = inc["candidates"] or [inc["action"]]
    action = cands[min(body.action_index, len(cands) - 1)] if cands else {"type": "manual", "params": {}}
    # Pre-flight: the world may have changed since the agent's dry run - re-check before touching anything.
    edges = (await servicemap.build()).get("edges", [])
    pre = await remediation.dry_run(action, edges)
    if not pre["ok"]:
        failed = "; ".join(f"{c['name']}: {c['detail']}" for c in pre["checks"] if not c["ok"])
        cands[min(body.action_index, len(cands) - 1)]["dry_run"] = pre
        db.update("incidents", iid, {"candidates": cands})
        raise HTTPException(409, f"pre-flight dry run failed, nothing was changed - {failed}")
    db.update("incidents", iid, {"status": "remediating", "approved_at": time.time(), "approver": body.approver,
                                 "action": action})
    try:
        res = await remediation.execute(action, iid, body.approver)
    except Exception as e:
        res = {"ok": False, "detail": f"{type(e).__name__}: {e}"}
    ex = {"ts": time.time(), "approver": body.approver, "owner": inc["owner"], "comment": body.comment,
          "action": action, "preflight": pre, "result": res}
    if action["type"] == "manual":
        db.update("incidents", iid, {"status": "resolved", "resolved_at": time.time(), "execution": ex})
    else:
        db.update("incidents", iid, {"status": "verifying" if res["ok"] else "remediation_failed", "execution": ex})
        if res["ok"]:
            asyncio.create_task(_verify(iid))
    return db.one("SELECT * FROM incidents WHERE id=?", (iid,))


@app.post("/api/incidents/{iid}/reject")
async def reject(iid: int, body: Approval):
    db.update("incidents", iid, {"status": "rejected", "approver": body.approver, "resolved_at": time.time(),
                                 "execution": {"ts": time.time(), "approver": body.approver, "rejected": True,
                                               "comment": body.comment}})
    await notify.send(db.one("SELECT * FROM incidents WHERE id=?", (iid,)), "rejected")
    return {"ok": True}


@app.post("/api/incidents/{iid}/close")
async def close(iid: int):
    db.update("incidents", iid, {"status": "closed", "resolved_at": time.time()})
    return {"ok": True}


@app.post("/api/incidents/{iid}/reanalyze")
async def reanalyze(iid: int):
    db.update("incidents", iid, {"status": "open", "steps": []})
    asyncio.create_task(detector._safe_analyze(iid))
    return {"ok": True}


class Feedback(BaseModel):
    score: int
    rca_correct: bool = True
    comment: str = ""


@app.post("/api/incidents/{iid}/feedback")
async def feedback(iid: int, body: Feedback):
    """Improve Score: engineers rate the RCA. Good + resolved analyses become runbooks in incident memory;
    poor ones lower a reused runbook's score (disabled below 2.5) and are fed back as lessons to the LLM."""
    inc = db.one("SELECT * FROM incidents WHERE id=?", (iid,))
    if not inc:
        raise HTTPException(404)
    score = max(1, min(5, body.score))
    db.update("incidents", iid, {"score": score, "feedback": body.comment, "rca_correct": int(body.rca_correct)})
    msg = "feedback saved"
    if inc["runbook_id"]:
        db.ex("UPDATE runbooks SET score_sum=score_sum+?, score_n=score_n+1, updated_at=? WHERE id=?",
              (score, time.time(), inc["runbook_id"]))
        rb = db.one("SELECT * FROM runbooks WHERE id=?", (inc["runbook_id"],))
        if rb["score_n"] >= 2 and rb["score_sum"] / rb["score_n"] < 2.5:
            db.ex("UPDATE runbooks SET enabled=0 WHERE id=?", (rb["id"],))
            msg = f"RB-{rb['id']} disabled (avg score below 2.5)"
    elif score >= 4 and body.rca_correct and inc["action"] and inc["status"] in ("resolved", "verifying"):
        sig = agent.signature(inc["kind"], inc["facts"] or {}, inc["action"])
        rid = db.insert("runbooks", {
            "signature": sig, "title": inc["title"], "kind": inc["kind"], "skill": inc["skill"],
            "root_cause": inc["root_cause"], "runbook": inc["runbook"], "action": inc["action"], "uses": 0,
            "score_sum": score, "score_n": 1, "enabled": 1, "source_incident": iid, "created_at": time.time(),
            "updated_at": time.time()}) if not db.one("SELECT id FROM runbooks WHERE signature=?", (sig,)) else None
        if rid:
            db.update("incidents", iid, {"runbook_id": rid})
            msg = f"saved to incident memory as RB-{rid}"
    return {"ok": True, "message": msg}


@app.get("/api/runbooks")
async def runbooks():
    return db.q("SELECT * FROM runbooks ORDER BY id DESC")


@app.post("/api/runbooks/{rid}/toggle")
async def toggle_runbook(rid: int):
    db.ex("UPDATE runbooks SET enabled=1-enabled WHERE id=?", (rid,))
    return {"ok": True}


@app.get("/api/skills")
async def skills():
    out = []
    for k, s in agent.SKILLS.items():
        rows = db.q("SELECT score, rca_correct, analysis_ms, llm_ok FROM incidents WHERE skill=?", (k,))
        sc = [r["score"] for r in rows if r["score"]]
        rc = [r["rca_correct"] for r in rows if r["rca_correct"] is not None]
        ms = [r["analysis_ms"] for r in rows if r["analysis_ms"]]
        out.append({"id": k, **s, "runs": len(rows), "avg_score": round(sum(sc) / len(sc), 2) if sc else None,
                    "accuracy": round(sum(rc) / len(rc), 2) if rc else None,
                    "avg_analysis_s": round(sum(ms) / len(ms) / 1000, 1) if ms else None,
                    "lessons": agent.lessons(k)})
    return out


@app.get("/api/notifications")
async def notifications():
    return db.q("SELECT id,ts,channel,incident_id,event,status FROM notifications ORDER BY id DESC LIMIT 100")


# ---------------- settings ----------------
@app.get("/api/settings")
async def get_settings():
    return {"settings": db.settings(), "llm": await llm.status(), "public_url": PUBLIC_URL, "grafana_url": GRAFANA_URL}


@app.put("/api/settings")
async def put_settings(body: dict):
    for k, v in body.items():
        if k in db.DEFAULT_SETTINGS:
            db.ex("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, str(v)))
    return db.settings()


@app.post("/api/settings/test-teams")
async def test_teams():
    fake = {"id": 0, "title": "Test notification from AIOps One Solution", "entity_type": "service",
            "entity": "demo", "severity": "info", "status": "test"}
    await notify.send(fake, "detected")
    return db.one("SELECT status FROM notifications ORDER BY id DESC LIMIT 1")


# ---------------- chaos / demo scenarios ----------------
async def _post(url: str, body: dict):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(url, json=body)
        r.raise_for_status()
        return r.json()


@app.post("/api/chaos/{scenario}")
async def chaos(scenario: str):
    if scenario == "bad_deploy":
        commit = "%07x" % random.randrange(16**7)
        return await record_deploy(DeployIn(service="payment", version="1.3.0", commit=commit, author="dev-somchai",
                                            message="feat(payment): apply member discount at charge time",
                                            profile="bad"))
    if scenario == "slow_db":
        return await remediation.set_app_state("inventory", {
            "latency_ms": 1600, "latency_msg": "slow query: SELECT * FROM stock WHERE sku=$1 took {ms}ms - "
                                               "connection pool exhausted (20/20 in use, 37 waiting)"})
    if scenario == "cpu_hog":
        return await _post("http://payment:8000/admin/cpu", {"seconds": 600, "workers": 3})
    if scenario == "brute_force":
        return await _post("http://loadgen:8000/admin/attack", {"seconds": 240, "ip": "203.0.113.77"})
    if scenario == "instance_fault":
        return await _post("http://frontend-b:8000/admin/state", {
            "error_rate": 0.5, "error_msg": "RedisTimeoutError: session cache unreachable from frontend-b "
                                            "(connection pool stuck after network blip)"})
    if scenario == "reset":
        with open(remediation.BLOCKLIST, "w") as f:
            f.write("# managed by AIOps remediation (owner-approved block_ip actions)\n")
        await tm.container_exec(remediation.FW_CONTAINER, ["nginx", "-s", "reload"])
        for a in db.q("SELECT service_name, admin_url FROM apps WHERE admin_url!=''"):
            try:
                await remediation.set_app_state(a["service_name"], {"error_rate": 0, "error_msg": "", "latency_ms": 0,
                                                                    "latency_msg": "", "blocked_ips": []})
            except Exception:
                pass
        try:
            await _post("http://loadgen:8000/admin/attack", {"seconds": 0})
        except Exception:
            pass
        return {"ok": True}
    raise HTTPException(404, "unknown scenario")


# ---------------- UI ----------------
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC, "vue", "index.html"))


@app.get("/legacy")
async def legacy_index():
    """Keep the pre-migration UI available until Vue feature parity is accepted."""
    return FileResponse(os.path.join(STATIC, "index.html"))


@app.get("/{frontend_path:path}")
async def vue_history_fallback(frontend_path: str):
    """Let Vue Router handle browser refreshes without masking missing API/static routes."""
    if frontend_path.split("/", 1)[0] in {"api", "static", "install"}:
        raise HTTPException(404)
    return FileResponse(os.path.join(STATIC, "vue", "index.html"))
