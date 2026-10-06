"""Thin read-only clients for Prometheus, Loki, Tempo and Docker.

These are the only things the agent's tools are allowed to call — nothing here
changes state in the customer environment.
"""
import asyncio
import base64
import math
import os
import re
import time

import httpx

PROM = os.environ.get("PROM_URL", "http://prometheus:9090")
LOKI = os.environ.get("LOKI_URL", "http://loki:3100")
TEMPO = os.environ.get("TEMPO_URL", "http://tempo:3200")

CALLS = "traces_span_metrics_calls_total"
DUR = "traces_span_metrics_duration_milliseconds_bucket"
SRV = 'span_kind="SPAN_KIND_SERVER"'

_client = httpx.AsyncClient(timeout=15)


# ---------------- Prometheus ----------------
async def prom(expr: str) -> list:
    try:
        r = await _client.get(f"{PROM}/api/v1/query", params={"query": expr})
        return r.json().get("data", {}).get("result", [])
    except Exception:
        return []


async def prom_value(expr: str) -> float | None:
    res = await prom(expr)
    if not res:
        return None
    v = float(res[0]["value"][1])
    return None if math.isnan(v) or math.isinf(v) else v


async def prom_range(expr: str, minutes: int = 30, step: int = 30) -> list:
    end = time.time()
    try:
        r = await _client.get(f"{PROM}/api/v1/query_range",
                              params={"query": expr, "start": end - minutes * 60, "end": end, "step": step})
        res = r.json().get("data", {}).get("result", [])
    except Exception:
        return []
    out = []
    for s in res:
        pts = []
        for t, v in s["values"]:
            f = float(v)
            pts.append([t, None if math.isnan(f) or math.isinf(f) else round(f, 4)])
        out.append({"labels": s["metric"], "points": pts})
    return out


def svc_expr(svc: str, metric: str, window: str = "1m") -> str:
    sel = f'service_name="{svc}",{SRV}'
    if metric == "rps":
        return f"sum(rate({CALLS}{{{sel}}}[{window}]))"
    if metric == "error_rate":
        return (f'(sum(rate({CALLS}{{{sel},status_code="STATUS_CODE_ERROR"}}[{window}])) or vector(0))'
                f" / sum(rate({CALLS}{{{sel}}}[{window}]))")
    if metric == "p95":
        return f"histogram_quantile(0.95, sum by (le) (rate({DUR}{{{sel}}}[{window}])))"
    raise ValueError(metric)


def host_expr(host: str, metric: str) -> str:
    sel = f'job="infra",host="{host}"'
    return {
        "cpu": f'100 * (1 - avg(rate(node_cpu_seconds_total{{{sel},mode="idle"}}[1m])))',
        "mem": f"100 * (1 - node_memory_MemAvailable_bytes{{{sel}}} / node_memory_MemTotal_bytes{{{sel}}})",
        "disk": f'100 * (1 - node_filesystem_avail_bytes{{{sel},mountpoint="/"}} / node_filesystem_size_bytes{{{sel},mountpoint="/"}})',
        "load": f"node_load1{{{sel}}}",
        "up": f"up{{{sel}}}",
    }[metric]


async def error_rate_by_version(svc: str, window: str = "2m") -> list[dict]:
    sel = f'service_name="{svc}",{SRV}'
    errs = await prom(f'sum by (app_version, app_commit) (rate({CALLS}{{{sel},status_code="STATUS_CODE_ERROR"}}[{window}]))')
    tot = await prom(f"sum by (app_version, app_commit) (rate({CALLS}{{{sel}}}[{window}]))")
    emap = {(e["metric"].get("app_version"), e["metric"].get("app_commit")): float(e["value"][1]) for e in errs}
    out = []
    for t in tot:
        k = (t["metric"].get("app_version"), t["metric"].get("app_commit"))
        total = float(t["value"][1])
        if total > 0:
            out.append({"version": k[0], "commit": k[1], "rps": round(total, 3),
                        "error_rate": round(emap.get(k, 0.0) / total, 4)})
    return sorted(out, key=lambda x: -x["error_rate"])


# ---------------- Loki ----------------
async def loki_logs(selector: str, minutes: int = 10, limit: int = 60, line_filter: str = "") -> list[dict]:
    end = time.time_ns()
    query = selector + (f" {line_filter}" if line_filter else "")
    try:
        r = await _client.get(f"{LOKI}/loki/api/v1/query_range", params={
            "query": query, "start": end - minutes * 60 * 10**9, "end": end,
            "limit": limit, "direction": "backward"})
        streams = r.json().get("data", {}).get("result", [])
    except Exception:
        return []
    out = []
    for s in streams:
        lab = s.get("stream", {})
        for ts, line in s.get("values", []):
            out.append({"ts": int(ts) / 1e9, "service": lab.get("service_name"),
                        "level": lab.get("severity_text") or lab.get("detected_level"),
                        "trace_id": lab.get("trace_id"), "line": line})
    out.sort(key=lambda x: -x["ts"])
    return out[:limit]


async def loki_count(query: str) -> float:
    try:
        r = await _client.get(f"{LOKI}/loki/api/v1/query", params={"query": query})
        res = r.json().get("data", {}).get("result", [])
        return sum(float(x["value"][1]) for x in res)
    except Exception:
        return 0.0


_NORM = re.compile(r"\b(tx)?\d+(\.\d+)?\b|\b[0-9a-f]{7,40}\b|ip=\S+|user=\S+")


def fingerprint(line: str) -> str:
    return _NORM.sub("<*>", line)[:140]


def top_messages(logs: list[dict], n: int = 5) -> list[dict]:
    counts: dict[str, dict] = {}
    for lg in logs:
        fp = fingerprint(lg["line"])
        c = counts.setdefault(fp, {"pattern": fp, "count": 0, "example": lg["line"], "service": lg["service"],
                                   "level": lg["level"]})
        c["count"] += 1
    return sorted(counts.values(), key=lambda x: -x["count"])[:n]


# ---------------- Tempo ----------------
async def tempo_search(traceql: str, minutes: int = 10, limit: int = 20) -> list[dict]:
    end = int(time.time())
    try:
        r = await _client.get(f"{TEMPO}/api/search", params={"q": traceql, "limit": limit,
                                                             "start": end - minutes * 60, "end": end})
        return r.json().get("traces", []) or []
    except Exception:
        return []


def _b64hex(v: str | None) -> str | None:
    if not v:
        return None
    if re.fullmatch(r"[0-9a-fA-F]{16}", v):
        return v.lower()
    try:
        return base64.b64decode(v).hex()
    except Exception:
        return v


def _attr(attrs: list, key: str):
    for a in attrs or []:
        if a.get("key") == key:
            val = a.get("value", {})
            return next(iter(val.values()), None) if val else None
    return None


async def tempo_trace(trace_id: str) -> list[dict]:
    """Flatten a Tempo trace into spans: id, parent, service, name, start/end ms, error, status msg."""
    try:
        r = await _client.get(f"{TEMPO}/api/traces/{trace_id}")
        data = r.json()
    except Exception:
        return []
    batches = data.get("batches") or data.get("resourceSpans") or data.get("trace", {}).get("resourceSpans") or []
    spans = []
    for b in batches:
        svc = _attr(b.get("resource", {}).get("attributes"), "service.name")
        inst = _attr(b.get("resource", {}).get("attributes"), "service.instance.id") or svc
        for ss in b.get("scopeSpans") or b.get("instrumentationLibrarySpans") or []:
            for sp in ss.get("spans", []):
                st = sp.get("status", {}) or {}
                code = st.get("code")
                spans.append({
                    "id": _b64hex(sp.get("spanId")), "parent": _b64hex(sp.get("parentSpanId")),
                    "service": svc, "instance": inst, "name": sp.get("name"),
                    "start": int(sp.get("startTimeUnixNano", 0)) / 1e6,
                    "end": int(sp.get("endTimeUnixNano", 0)) / 1e6,
                    "error": code in (2, "STATUS_CODE_ERROR"), "status_msg": st.get("message", ""),
                    "version": _attr(sp.get("attributes"), "app.version"),
                    "kind": sp.get("kind"),
                })
    spans.sort(key=lambda s: s["start"])
    return spans


def error_origin(spans: list[dict]) -> list[dict]:
    """Error spans with no erroring child — the deepest point where the failure started."""
    children: dict[str, list] = {}
    for s in spans:
        children.setdefault(s["parent"], []).append(s)
    return [s for s in spans if s["error"] and not any(c["error"] for c in children.get(s["id"], []))]


def self_time(spans: list[dict]) -> dict[str, float]:
    children: dict[str, list] = {}
    for s in spans:
        children.setdefault(s["parent"], []).append(s)
    out: dict[str, float] = {}
    for s in spans:
        dur = s["end"] - s["start"]
        kids = sum(c["end"] - c["start"] for c in children.get(s["id"], []))
        out[s["service"]] = out.get(s["service"], 0) + max(dur - kids, 0)
    return out


def parse_json_lines(logs: list[dict]) -> list[dict]:
    """Network devices log one JSON object per line."""
    import json as _json
    out = []
    for lg in logs:
        try:
            d = _json.loads(lg["line"])
        except ValueError:
            continue
        d["ts"] = lg["ts"]
        out.append(d)
    return out


async def edge_logs(device: str, minutes: int = 5, limit: int = 2000, line_filter: str = "") -> list[dict]:
    return parse_json_lines(await loki_logs(f'{{service_name="{device}"}}', minutes=minutes, limit=limit,
                                            line_filter=line_filter))


# ---------------- Docker (read-only listing) ----------------
def _ip_map() -> dict[str, str]:
    m = {}
    for c in docker_client().containers.list():
        for net in (c.attrs.get("NetworkSettings", {}).get("Networks") or {}).values():
            if net.get("IPAddress"):
                m[net["IPAddress"]] = c.name
    return m


async def container_ip_map() -> dict[str, str]:
    try:
        return await asyncio.to_thread(_ip_map)
    except Exception:
        return {}


def _container_info(name: str) -> dict | None:
    try:
        c = docker_client().containers.get(name)
        return {"name": c.name, "status": c.status, "restart_count": c.attrs.get("RestartCount", 0),
                "started_at": c.attrs.get("State", {}).get("StartedAt")}
    except Exception:
        return None


async def container_info(name: str) -> dict | None:
    return await asyncio.to_thread(_container_info, name)


def _exec(name: str, cmd: list[str]) -> tuple[int, str]:
    r = docker_client().containers.get(name).exec_run(cmd)
    return r.exit_code, (r.output or b"").decode(errors="replace")


async def container_exec(name: str, cmd: list[str]) -> tuple[int, str]:
    return await asyncio.to_thread(_exec, name, cmd)

_docker = None


def docker_client():
    global _docker
    if _docker is None:
        import docker
        _docker = docker.from_env()
    return _docker


def _container_stats(c) -> dict:
    try:
        s = c.stats(stream=False)
        cpu_d = s["cpu_stats"]["cpu_usage"]["total_usage"] - s["precpu_stats"]["cpu_usage"]["total_usage"]
        sys_d = s["cpu_stats"].get("system_cpu_usage", 0) - s["precpu_stats"].get("system_cpu_usage", 0)
        ncpu = s["cpu_stats"].get("online_cpus") or 1
        cpu = (cpu_d / sys_d) * ncpu * 100 if sys_d > 0 else 0.0
        mem = s["memory_stats"].get("usage", 0) / 2**20
        lim = s["memory_stats"].get("limit", 0) / 2**20
    except Exception:
        cpu, mem, lim = 0.0, 0.0, 0.0
    return {"name": c.name, "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "status": c.status, "cpu_pct": round(cpu, 1), "mem_mb": round(mem, 1), "mem_limit_mb": round(lim)}


def _list_containers(with_stats: bool) -> list[dict]:
    cs = docker_client().containers.list(all=True)
    if not with_stats:
        return [{"name": c.name, "image": c.image.tags[0] if c.image.tags else "", "status": c.status} for c in cs]
    from concurrent.futures import ThreadPoolExecutor
    running = [c for c in cs if c.status == "running"]
    with ThreadPoolExecutor(8) as ex:
        stats = list(ex.map(_container_stats, running))
    return sorted(stats, key=lambda x: -x["cpu_pct"])


async def containers(with_stats: bool = False) -> list[dict]:
    try:
        return await asyncio.to_thread(_list_containers, with_stats)
    except Exception as e:
        return [{"error": str(e)}]
