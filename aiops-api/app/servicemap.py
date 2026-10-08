"""Smartscape-style service map built from two sources:

  traced     - parent/child spans in sampled Tempo traces (services that run OpenTelemetry);
               rates come from span metrics, edge throughput = callee rate x share of its calls from this caller.
  discovered - processes, containers and TCP connections reported by the host agent;
               no request rates, but the box and the line appear as soon as a computer is connected.
"""
import asyncio
import time
from collections import Counter

from . import repo
from . import telemetry as tm

_cache = {"ts": 0.0, "data": None}
SEEN_FRESH_S = 180


async def _inst_metrics(svc: str) -> dict[str, dict]:
    sel = f'service_name="{svc}",{tm.SRV}'
    tot = await tm.prom(f"sum by (exported_instance) (rate({tm.CALLS}{{{sel}}}[1m]))")
    err = await tm.prom(f'sum by (exported_instance) (rate({tm.CALLS}{{{sel},status_code="STATUS_CODE_ERROR"}}[1m]))')
    p95 = await tm.prom(f"histogram_quantile(0.95, sum by (le, exported_instance) (rate({tm.DUR}{{{sel}}}[1m])))")
    emap = {e["metric"].get("exported_instance"): float(e["value"][1]) for e in err}
    pmap = {e["metric"].get("exported_instance"): float(e["value"][1]) for e in p95}
    out = {}
    for t in tot:
        i = t["metric"].get("exported_instance") or svc
        r = float(t["value"][1])
        p = pmap.get(i)
        out[i] = {"rps": round(r, 3), "error_rate": round(emap.get(i, 0) / r, 4) if r else 0.0,
                  "p95_ms": round(p, 1) if p is not None and p == p else None}
    return out


def _edge_list(counter: Counter, rate_of) -> list[dict]:
    incoming = Counter()
    for (_, b), c in counter.items():
        incoming[b] += c
    out = []
    for (a, b), c in counter.items():
        share = c / incoming[b] if incoming[b] else 0
        r, e = rate_of(b)
        out.append({"from": a, "to": b, "type": "traced", "samples": c, "share": round(share, 3),
                    "rps": round(share * r, 3) if r is not None else None, "error_rate": e})
    return out


async def build(minutes: int = 5, max_traces: int = 14, force: bool = False) -> dict:
    if not force and _cache["data"] and time.time() - _cache["ts"] < 20:
        return _cache["data"]
    traces = await tm.tempo_search("{ }", minutes=minutes, limit=60)
    spans_all = list(await asyncio.gather(*(tm.tempo_trace(t["traceID"]) for t in traces[:max_traces])))
    # The latest traces are dominated by the busiest app; top up with a couple of traces from every traced service
    # that did not appear, so quiet apps (e.g. ones the host agent traces with eBPF) still get their arrows.
    seen = {s["service"] for spans in spans_all for s in spans}
    quiet = [r["service_name"] for r in repo.list_services(("service",)) if r["service_name"] not in seen]
    extra = await asyncio.gather(*(tm.tempo_search(f'{{ resource.service.name = "{n}" }}', minutes=minutes, limit=2)
                                   for n in quiet))
    ids = {t["traceID"] for t in traces[:max_traces]}
    more = list(dict.fromkeys(t["traceID"] for ts in extra for t in ts if t["traceID"] not in ids))[:max_traces]
    spans_all += await asyncio.gather(*(tm.tempo_trace(i) for i in more))
    svc_edges, inst_edges, inst_of, roots = Counter(), Counter(), {}, Counter()
    for spans in spans_all:
        by_id = {s["id"]: s for s in spans}
        for s in spans:
            inst_of[s["instance"]] = s["service"]
            par = by_id.get(s["parent"])
            if not par:
                if not s["parent"]:
                    roots[s["service"]] += 1
                continue
            if par["service"] != s["service"]:
                svc_edges[(par["service"], s["service"])] += 1
                inst_edges[(par["instance"], s["instance"])] += 1

    registered = {s["service_name"]: s for s in repo.list_services(("service", "network", "process", "external"))}
    names = sorted(set(registered) | {n for e in svc_edges for n in e})
    traced_names = [n for n in names if (registered.get(n) or {}).get("kind") not in ("process", "external")]
    metrics = dict(zip(traced_names, await asyncio.gather(*(_inst_metrics(n) for n in traced_names))))
    problems = repo.open_problem_targets()

    def problem_for(name: str):
        for p in problems:
            ps = p["params"] or {}
            if name in (p["entity"], ps.get("service"), ps.get("instance")):
                return p["id"]
        return None

    now = time.time()
    nodes = []
    for n in names:
        a = registered.get(n, {})
        im = metrics.get(n, {})
        rps = sum(v["rps"] for v in im.values()) if im else None
        err = (sum(v["rps"] * v["error_rate"] for v in im.values()) / rps) if rps else None
        p95s = [v["p95_ms"] for v in im.values() if v["p95_ms"] is not None]
        seen = max([i.get("last_seen") or 0 for i in a.get("instances") or []], default=0)
        nodes.append({
            "id": n, "name": a.get("display_name") or n, "kind": a.get("kind") or "service",
            "source": a.get("source") or "traced", "language": a.get("language"), "owner": a.get("owner"),
            "hosts": a.get("hosts") or [], "connected": n in registered, "traced": bool(im),
            "rps": round(rps, 3) if rps is not None else None, "error_rate": round(err, 4) if err is not None else None,
            "p95_ms": max(p95s) if p95s else None,
            "instances": [{"id": i, **v, "problem_id": problem_for(i)} for i, v in sorted(im.items())] if len(im) > 1 else [],
            "seen_recently": bool(seen and now - seen < SEEN_FRESH_S), "last_seen": seen or None,
            "entry_url": a.get("entry_url"), "problem_id": problem_for(n)})

    by = {n["id"]: n for n in nodes}
    edges = _edge_list(svc_edges, lambda b: (by.get(b, {}).get("rps"), by.get(b, {}).get("error_rate")))
    have = {(e["from"], e["to"]) for e in edges}
    for d in repo.discovered_edges():
        if (d["from"], d["to"]) not in have and d["from"] in by and d["to"] in by:
            edges.append({"from": d["from"], "to": d["to"], "type": "network", "samples": d["samples"],
                          "share": None, "rps": None, "error_rate": None, "last_seen": d["last_seen"]})

    multi = {n["id"] for n in nodes if n["instances"]}
    inst_rate = {i: v for n in traced_names for i, v in metrics[n].items()}
    iedges = [e for e in _edge_list(inst_edges, lambda b: (inst_rate.get(b, {}).get("rps"), inst_rate.get(b, {}).get("error_rate")))
              if inst_of.get(e["to"]) in multi or inst_of.get(e["from"]) in multi]
    for e in iedges:
        e["from_service"], e["to_service"] = inst_of.get(e["from"]), inst_of.get(e["to"])

    entries = [r for r, _ in roots.most_common()]
    entries += [n["id"] for n in nodes if n["entry_url"] and n["id"] not in entries]
    hosts = [{"name": h["name"], "kind": h["kind"], "os": h["os"], "agent": h["agent"]} for h in repo.list_hosts()]
    data = {"nodes": nodes, "edges": edges, "instance_edges": iedges, "entry": entries, "hosts": hosts,
            "traces_sampled": len([s for s in spans_all if s]), "ts": now}
    _cache.update(ts=now, data=data)
    return data
