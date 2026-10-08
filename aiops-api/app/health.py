"""Live health of services and hosts (metrics from Prometheus + open problems from the database)."""
import asyncio
import time

from . import db, repo
from . import telemetry as tm

SEEN_FRESH_S = 180


def _problem_index() -> dict[str, int]:
    idx = {}
    for p in repo.open_problem_targets():
        for k in (p["entity"], (p["params"] or {}).get("service"), (p["params"] or {}).get("instance")):
            if k and k not in idx:
                idx[k] = p["id"]
    return idx


async def service_health(s: dict, problems: dict | None = None) -> dict:
    name = s["service_name"]
    problems = problems if problems is not None else _problem_index()
    dep = repo.deployments(name, limit=1)
    dep = dep[0] if dep else None
    out = {"service": name, "name": s.get("display_name") or name, "kind": s["kind"], "source": s["source"],
           "language": s.get("language"), "owner": s.get("owner"), "hosts": s.get("hosts") or [],
           "instrumentation": s.get("instrumentation"),
           "problem_id": problems.get(name), "version": dep and dep["version"], "commit": dep and dep["commit_hash"],
           "deployed_at": dep and dep["ts"], "rps": None, "error_rate": None, "p95_ms": None}
    if s["kind"] in ("process", "external"):
        seen = max([i.get("last_seen") or 0 for i in s.get("instances") or []], default=0)
        out["last_seen"] = seen or None
        out["status"] = "problem" if out["problem_id"] else ("healthy" if seen and time.time() - seen < SEEN_FRESH_S
                                                             else "no-data")
        return out
    rps, err, p95 = await asyncio.gather(tm.prom_value(tm.svc_expr(name, "rps")),
                                         tm.prom_value(tm.svc_expr(name, "error_rate")),
                                         tm.prom_value(tm.svc_expr(name, "p95")))
    out.update(rps=rps, error_rate=err, p95_ms=p95)
    out["status"] = "no-data" if rps is None else ("problem" if out["problem_id"] else "healthy")
    return out


async def services_health(kinds=("service", "network", "process", "external")) -> list[dict]:
    problems = _problem_index()
    svcs = repo.list_services(kinds)
    return list(await asyncio.gather(*(service_health(s, problems) for s in svcs)))


async def host_health(h: dict, problems: dict | None = None) -> dict:
    problems = problems if problems is not None else _problem_index()
    up, cpu, mem, disk, load = await asyncio.gather(*(tm.prom_value(tm.host_expr(h["name"], m))
                                                      for m in ("up", "cpu", "mem", "disk", "load")))
    pid = problems.get(h["name"])
    if up is None or (up == 0 and h.get("kind") == "workstation"):
        status = "offline" if h.get("agent") == "aiops-agent" else "no-data"
    else:
        status = "down" if up == 0 else ("problem" if pid else "healthy")
    services = [r["service_name"] for r in db.q("""SELECT DISTINCT s.service_name FROM service_instances i
                 JOIN services s ON s.id=i.service_id JOIN hosts hh ON hh.id=i.host_id WHERE hh.name=%s ORDER BY 1""",
                                                (h["name"],))]
    return {**h, "up": up, "cpu": cpu, "mem": mem, "disk": disk, "load": load, "status": status,
            "problem_id": pid, "services": services}


async def hosts_health() -> list[dict]:
    problems = _problem_index()
    return list(await asyncio.gather(*(host_health(h, problems) for h in repo.list_hosts())))
