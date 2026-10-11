"""Real-time anomaly detection.

Every 15 s, for every connected service and host:
  * each metric is compared with what is normal for *that* host or service at this time of day, learned from
    Prometheus history (baseline.py) - so a machine that always runs at 90% CPU is fine, and the same machine
    dropping to 5% is not. Fixed limits from settings only apply while a metric is still being learned, and a
    few safety limits (a nearly full disk) always apply.
  * anomaly = outside the normal band for several consecutive checks (hosts wait longer than services)
  * related anomalies within 10 min are merged into one problem (like Dynatrace Davis)
  * error-rate anomalies are pinned to the version/commit where errors started
"""
import asyncio
import time
import traceback

import os

from . import agent, baseline, db, llm, notify, repo
from . import telemetry as tm

INTERVAL = 15
HISTORY_MIN = 8 * 24 * 60   # as far back as Prometheus keeps (retention 8d)
REFRESH_S = 600             # re-learn each band every 10 minutes
STREAK = {"host_cpu": 4, "host_mem": 4, "host_disk": 4, "traffic_drop": 4}  # checks in a row before raising; default 2
_bands: dict[str, dict] = {}
_streak: dict[str, dict] = {}
LAST_RUN = {"ts": 0, "checks": 0, "error": None}

# the fixed limit used while a metric has too little history to learn from
FALLBACK = {"cpu": "cpu_threshold", "mem": "mem_threshold", "disk": "disk_threshold",
            "error_rate": "err_threshold", "p95": "p95_threshold_ms"}
LOW_LABEL = {"host_cpu": "CPU unusually low", "host_mem": "Memory dropped sharply"}


async def band(key: str, expr: str) -> dict | None:
    """Normal band for one metric of one entity, cached and re-learned every REFRESH_S."""
    b = _bands.get(key)
    if b and time.time() - b["ts"] < REFRESH_S:
        return b["band"]
    series = await tm.prom_range(expr, minutes=HISTORY_MIN, step=300)
    pts = [(float(t), v) for t, v in (series[0]["points"] if series else []) if v is not None]
    learned = baseline.learn(pts, exclude=_incident_windows(key))
    _bands[key] = {"band": learned, "ts": time.time()}
    return learned


def _incident_windows(key: str) -> list[tuple[float, float]]:
    """Periods to leave out of learning. A service incident disturbs the whole request path, so every service
    skips every service incident; a host skips only its own."""
    metric, entity = key.split("|", 1)
    host_metric = metric in ("cpu", "mem", "disk")
    out = []
    for i in repo.list_incidents(limit=500):
        mine = i["entity"] == entity if host_metric else i["entity_type"] == "service"
        if mine:
            out.append((i["detected_at"] - 900, (i.get("resolved_at") or time.time()) + 300))
    return out


async def assess(key: str, metric: str, expr: str, value: float | None) -> dict:
    """Value vs this entity's normal: {state, limit_low, limit_high, reason, band}."""
    b = await band(key, expr)
    fb = db.fsetting(FALLBACK[metric]) if metric in FALLBACK else None
    r = baseline.judge(metric, value, b, db.setting("sensitivity") or "normal", fb)
    r["band"] = b
    return r


def _signal(kind: str, etype: str, entity: str, value: float, unit: str, r: dict, digits: int = 1, **extra) -> dict:
    b = r["band"] or {}
    low = r["state"] == "low"
    return {"kind": kind, "entity_type": etype, "entity": entity, "value": round(value, digits), "unit": unit,
            "direction": r["state"], "reason": r["reason"],
            "threshold": round((r["limit_low"] if low else r["limit_high"]) or 0, digits),
            "baseline": round(b["median"], digits) if b else None,
            "normal_low": round(b["low"], digits) if b else None, "normal_high": round(b["high"], digits) if b else None,
            "learned_from": b.get("source"), "learned_days": b.get("days"), **extra}


PLATFORM_HOST = os.environ.get("PLATFORM_HOST", "cp26pt1")


def open_incident(entity: str, kind: str) -> dict | None:
    return repo.open_incident(entity, kind)


def related_incident(kind: str) -> dict | None:
    return repo.related_incident(kind, time.time() - 600)


async def raise_signal(sig: dict):
    key = f"{sig['kind']}|{sig['entity']}"
    st = _streak.setdefault(key, {"n": 0, "first": time.time()})
    if st["n"] == 0:
        st["first"] = time.time()
    st["n"] += 1
    if st["n"] < STREAK.get(sig["kind"], 2) or open_incident(sig["entity"], sig["kind"]):
        return
    rel = related_incident(sig["kind"]) if sig["entity_type"] == "service" else None
    if rel:
        if sig["entity"] != rel["entity"]:
            repo.add_affected(rel["id"], sig["entity"])
        return
    if sig["kind"] == "error_rate":
        sig["by_version"] = await tm.error_rate_by_version(sig["entity"])
    sev = "critical" if sig["kind"] in ("host_down", "error_rate") and sig["value"] > 3 * sig["threshold"] else "major"
    if sig["kind"] == "auth_bruteforce":
        sev = "major"
    label = LOW_LABEL.get(sig["kind"]) if sig.get("direction") == "low" else None
    title = f"{label or agent.KIND_LABEL[sig['kind']]} - {sig['entity']}"
    iid = repo.create_incident(title, sig["kind"], sev, sig["entity_type"], sig["entity"], sig,
                               started_at=st["first"] - INTERVAL)
    await notify.send(iid, "detected")
    if db.setting("auto_analyze") == "1":
        asyncio.create_task(_safe_analyze(iid))


async def _safe_analyze(iid: int):
    try:
        await agent.analyze(iid)
    except Exception as e:
        traceback.print_exc()
        repo.set_incident(iid, status="awaiting_approval", root_cause=f"Analysis failed: {e}")


def clear(kind: str, entity: str):
    _streak.pop(f"{kind}|{entity}", None)


SVC_METRICS = (("rps", "traffic_drop", "req/s", 2), ("error_rate", "error_rate", "ratio", 4), ("p95", "latency", "ms", 1))


async def check_service(svc: str) -> list[dict]:
    out = []
    rps = await tm.prom_value(tm.svc_expr(svc, "rps")) or 0.0
    r = await assess(f"rps|{svc}", "rps", tm.svc_expr(svc, "rps", "5m"), rps)
    (out.append(_signal("traffic_drop", "service", svc, rps, "req/s", r, 2)) if r["state"] == "low" else clear("traffic_drop", svc))
    if rps < 0.05:
        return out
    err = await tm.prom_value(tm.svc_expr(svc, "error_rate")) or 0.0
    r = await assess(f"err|{svc}", "error_rate", tm.svc_expr(svc, "error_rate", "5m"), err)
    (out.append(_signal("error_rate", "service", svc, err, "ratio", r, 4, rps=round(rps, 2)))
     if r["state"] == "high" else clear("error_rate", svc))
    p95 = await tm.prom_value(tm.svc_expr(svc, "p95"))
    if p95 is not None:
        r = await assess(f"p95|{svc}", "p95", tm.svc_expr(svc, "p95", "5m"), p95)
        (out.append(_signal("latency", "service", svc, p95, "ms", r)) if r["state"] == "high" else clear("latency", svc))
    return out


def _is_platform_host(host: str) -> bool:
    return host == PLATFORM_HOST


async def check_host(host: str) -> list[dict]:
    out = []
    self_noise = _is_platform_host(host) and llm.busy_recently()
    up = await tm.prom_value(tm.host_expr(host, "up"))
    hrow = repo.host(host) or {}
    if up == 0 and hrow.get("kind") == "workstation":
        return out  # a laptop leaving the network is "offline", not an outage
    if up == 0:
        out.append({"kind": "host_down", "entity_type": "host", "entity": host, "value": 1, "threshold": 0,
                    "baseline": 0, "unit": "down"})
        return out
    clear("host_down", host)
    for kind, m in (("host_cpu", "cpu"), ("host_mem", "mem"), ("host_disk", "disk")):
        v = await tm.prom_value(tm.host_expr(host, m))
        if v is None:
            continue
        r = await assess(f"{m}|{host}", m, tm.host_expr(host, m), v)
        # the AI itself loads the platform host's CPU while it investigates; that is not the host misbehaving
        if r["state"] in ("high", "low") and not (kind == "host_cpu" and self_noise and r["state"] == "high"):
            out.append(_signal(kind, "host", host, v, "%", r))
        else:
            clear(kind, host)
    return out


async def normal_ranges(etype: str, name: str) -> dict:
    """Current value next to its normal range, for the host and service pages."""
    if etype == "host":
        items = [(m, f"{m}|{name}", tm.host_expr(name, m), tm.host_expr(name, m)) for m in ("cpu", "mem", "disk")]
    else:
        items = [("rps", f"rps|{name}", tm.svc_expr(name, "rps"), tm.svc_expr(name, "rps", "5m")),
                 ("error_rate", f"err|{name}", tm.svc_expr(name, "error_rate"), tm.svc_expr(name, "error_rate", "5m")),
                 ("p95", f"p95|{name}", tm.svc_expr(name, "p95"), tm.svc_expr(name, "p95", "5m"))]
    out = {}
    for m, key, now_expr, hist_expr in items:
        v = await tm.prom_value(now_expr)
        r = await assess(key, m, hist_expr, v)
        b = r["band"]
        out[m] = {"value": v, "state": r["state"], "reason": r["reason"], "limit_low": r["limit_low"], "limit_high": r["limit_high"],
                  "normal_low": b["low"] if b else None, "normal_high": b["high"] if b else None,
                  "median": b["median"] if b else None, "learned_from": b["source"] if b else None, "days": b["days"] if b else 0}
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
    for a in repo.list_services(("service", "network")):
        sigs += await check_service(a["service_name"])
    for h in repo.list_hosts():
        sigs += await check_host(h["name"])
    sigs += await check_security()
    # Raise the strongest first: furthest beyond its limit (a drop counts by how far below it fell).
    def strength(s):
        if not s["threshold"]:
            return 0
        return -(s["threshold"] / max(s["value"], 1e-6)) if s.get("direction") == "low" else -(s["value"] / s["threshold"])
    sigs.sort(key=strength)
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
    if kind == "error_rate":  # back inside its own normal range - and the service the fix was applied to as well
        for svc in {ent, target}:
            v = await tm.prom_value(tm.svc_expr(svc, "error_rate"))
            r = await assess(f"err|{svc}", "error_rate", tm.svc_expr(svc, "error_rate", "5m"), v or 0.0)
            if r["state"] == "high":
                return False
        return True
    if kind == "latency":
        v = await tm.prom_value(tm.svc_expr(ent, "p95"))
        r = await assess(f"p95|{ent}", "p95", tm.svc_expr(ent, "p95", "5m"), v)
        return v is not None and r["state"] != "high"
    if kind == "traffic_drop":
        v = await tm.prom_value(tm.svc_expr(ent, "rps")) or 0.0
        return (await assess(f"rps|{ent}", "rps", tm.svc_expr(ent, "rps", "5m"), v))["state"] != "low"
    if kind == "auth_bruteforce":
        n = await tm.loki_count('sum(count_over_time({service_name="frontend"} |= "failed login" [1m]))')
        return n <= db.fsetting("auth_fail_per_min")
    sigs = await check_host(ent)
    return not any(s["kind"] == kind for s in sigs)
