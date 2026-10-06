"""Real-time anomaly detection.

Every 15 s, for every connected service and host:
  * adaptive baseline (EWMA mean/std) per signal + absolute floor from settings
  * anomaly = value above max(floor, mean + 4*std) for 2 consecutive checks
  * related anomalies within 10 min are merged into one problem (like Dynatrace Davis)
  * error-rate anomalies are pinned to the version/commit where errors started
"""
import asyncio
import math
import time
import traceback

from . import agent, db, llm, notify
from . import telemetry as tm

INTERVAL = 15
_base: dict[str, dict] = {}
_streak: dict[str, dict] = {}
LAST_RUN = {"ts": 0, "checks": 0, "error": None}


def _baseline_check(key: str, value: float, floor: float, min_std: float) -> tuple[bool, float, float]:
    b = _base.setdefault(key, {"mean": value, "var": 0.0, "n": 0})
    std = max(math.sqrt(b["var"]), min_std)
    limit = max(floor, b["mean"] + 4 * std) if b["n"] >= 8 else floor
    anomalous = value > limit
    if not anomalous:  # learn only from normal behaviour
        a = 0.1
        d = value - b["mean"]
        b["mean"] += a * d
        b["var"] = (1 - a) * (b["var"] + a * d * d)
        b["n"] += 1
    return anomalous, limit, b["mean"]


def open_incident(entity: str, kind: str) -> dict | None:
    return db.one("SELECT * FROM incidents WHERE entity=? AND kind=? AND status NOT IN ('resolved','rejected','closed') "
                  "ORDER BY id DESC LIMIT 1", (entity, kind))


def related_incident(kind: str) -> dict | None:
    return db.one("SELECT * FROM incidents WHERE kind=? AND status NOT IN ('resolved','rejected','closed') "
                  "AND detected_at>? ORDER BY id DESC LIMIT 1", (kind, time.time() - 600))


async def raise_signal(sig: dict):
    key = f"{sig['kind']}|{sig['entity']}"
    st = _streak.setdefault(key, {"n": 0, "first": time.time()})
    if st["n"] == 0:
        st["first"] = time.time()
    st["n"] += 1
    if st["n"] < 2 or open_incident(sig["entity"], sig["kind"]):
        return
    rel = related_incident(sig["kind"]) if sig["entity_type"] == "service" else None
    if rel:
        s = rel["signal"]
        affected = s.setdefault("affected", [])
        if sig["entity"] not in affected and sig["entity"] != rel["entity"]:
            affected.append(sig["entity"])
            db.update("incidents", rel["id"], {"signal": s})
        return
    if sig["kind"] == "error_rate":
        sig["by_version"] = await tm.error_rate_by_version(sig["entity"])
    sev = "critical" if sig["kind"] in ("host_down", "error_rate") and sig["value"] > 3 * sig["threshold"] else "major"
    if sig["kind"] == "auth_bruteforce":
        sev = "major"
    title = f"{agent.KIND_LABEL[sig['kind']]} - {sig['entity']}"
    iid = db.insert("incidents", {
        "title": title, "kind": sig["kind"], "entity_type": sig["entity_type"], "entity": sig["entity"],
        "severity": sev, "status": "open", "started_at": st["first"] - INTERVAL, "detected_at": time.time(),
        "signal": sig, "steps": []})
    inc = db.one("SELECT * FROM incidents WHERE id=?", (iid,))
    await notify.send(inc, "detected")
    if db.setting("auto_analyze") == "1":
        asyncio.create_task(_safe_analyze(iid))


async def _safe_analyze(iid: int):
    try:
        await agent.analyze(iid)
    except Exception as e:
        traceback.print_exc()
        db.update("incidents", iid, {"status": "awaiting_approval", "root_cause": f"Analysis failed: {e}",
                                     "action": {"type": "manual", "params": {}, "label": "Manual investigation"}})


def clear(kind: str, entity: str):
    _streak.pop(f"{kind}|{entity}", None)


async def check_service(svc: str) -> list[dict]:
    out = []
    rps = await tm.prom_value(tm.svc_expr(svc, "rps"))
    if not rps or rps < 0.05:
        return out
    err = await tm.prom_value(tm.svc_expr(svc, "error_rate")) or 0.0
    floor = db.fsetting("err_threshold")
    bad, limit, mean = _baseline_check(f"err|{svc}", err, floor, 0.01)
    (out.append({"kind": "error_rate", "entity_type": "service", "entity": svc, "value": round(err, 4),
                 "threshold": round(limit, 4), "baseline": round(mean, 4), "unit": "ratio", "rps": round(rps, 2)})
     if bad else clear("error_rate", svc))
    p95 = await tm.prom_value(tm.svc_expr(svc, "p95"))
    if p95 is not None:
        bad, limit, mean = _baseline_check(f"p95|{svc}", p95, db.fsetting("p95_threshold_ms"), 50)
        (out.append({"kind": "latency", "entity_type": "service", "entity": svc, "value": round(p95, 1),
                     "threshold": round(limit, 1), "baseline": round(mean, 1), "unit": "ms"})
         if bad else clear("latency", svc))
    return out


def _is_platform_host(host: str) -> bool:
    h = db.one("SELECT address FROM hosts WHERE name=?", (host,))
    return bool(h and h["address"].startswith("node-exporter"))


async def check_host(host: str) -> list[dict]:
    out = []
    self_noise = _is_platform_host(host) and llm.busy_recently()
    up = await tm.prom_value(tm.host_expr(host, "up"))
    if up == 0:
        out.append({"kind": "host_down", "entity_type": "host", "entity": host, "value": 1, "threshold": 0,
                    "baseline": 0, "unit": "down"})
        return out
    clear("host_down", host)
    for kind, m, key in (("host_cpu", "cpu", "cpu_threshold"), ("host_mem", "mem", "mem_threshold"),
                         ("host_disk", "disk", "disk_threshold")):
        v = await tm.prom_value(tm.host_expr(host, m))
        if v is None:
            continue
        floor = db.fsetting(key)
        if v > floor and not (kind == "host_cpu" and self_noise):
            out.append({"kind": kind, "entity_type": "host", "entity": host, "value": round(v, 1),
                        "threshold": floor, "baseline": None, "unit": "%"})
        else:
            clear(kind, host)
    return out


async def check_security() -> list[dict]:
    n = await tm.loki_count('sum(count_over_time({service_name="frontend"} |= "failed login" [1m]))')
    thr = db.fsetting("auth_fail_per_min")
    if n > thr:
        return [{"kind": "auth_bruteforce", "entity_type": "service", "entity": "frontend", "value": n,
                 "threshold": thr, "baseline": None, "unit": "failed logins/min"}]
    clear("auth_bruteforce", "frontend")
    return []


async def tick():
    sigs = []
    for a in db.q("SELECT service_name FROM apps"):
        sigs += await check_service(a["service_name"])
    for h in db.q("SELECT name FROM hosts"):
        sigs += await check_host(h["name"])
    sigs += await check_security()
    # Raise the most upstream-agnostic one first: highest value relative to threshold.
    sigs.sort(key=lambda s: -(s["value"] / s["threshold"]) if s["threshold"] else 0)
    for s in sigs:
        await raise_signal(s)
    LAST_RUN.update(ts=time.time(), checks=LAST_RUN["checks"] + 1, error=None, active_signals=len(sigs))


async def loop():
    await asyncio.sleep(10)
    while True:
        try:
            await tick()
        except Exception as e:
            LAST_RUN["error"] = str(e)
            traceback.print_exc()
        await asyncio.sleep(INTERVAL)


async def is_healthy(inc: dict) -> bool:
    kind, ent = inc["kind"], inc["entity"]
    act = inc.get("action") or {}
    target = act.get("params", {}).get("service") or ent
    if kind == "error_rate":
        v = await tm.prom_value(tm.svc_expr(ent, "error_rate"))
        v2 = await tm.prom_value(tm.svc_expr(target, "error_rate"))
        return (v or 0) < db.fsetting("err_threshold") and (v2 or 0) < db.fsetting("err_threshold")
    if kind == "latency":
        v = await tm.prom_value(tm.svc_expr(ent, "p95"))
        return v is not None and v < db.fsetting("p95_threshold_ms")
    if kind == "auth_bruteforce":
        n = await tm.loki_count('sum(count_over_time({service_name="frontend"} |= "failed login" [1m]))')
        return n <= db.fsetting("auth_fail_per_min")
    sigs = await check_host(ent)
    return not any(s["kind"] == kind for s in sigs)
