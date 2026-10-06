"""Smartscape-style service map.

Edges (who calls whom, down to the instance behind the load balancer) come from parent/child spans in
sampled Tempo traces. Rates come from span metrics, so edge throughput = callee rate x share of its calls
that came from this caller in the sample.
"""
import asyncio
import time
from collections import Counter

from . import db
from . import telemetry as tm

_cache = {"ts": 0.0, "data": None}


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
                  "p95_ms": round(p, 1) if p == p and p is not None else None}
    return out


async def build(minutes: int = 5, max_traces: int = 14) -> dict:
    if _cache["data"] and time.time() - _cache["ts"] < 20:
        return _cache["data"]
    traces = await tm.tempo_search("{ }", minutes=minutes, limit=60)
    spans_all = await asyncio.gather(*(tm.tempo_trace(t["traceID"]) for t in traces[:max_traces]))
    svc_edges, inst_edges, inst_of = Counter(), Counter(), {}
    roots = Counter()
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

    apps = {a["service_name"]: a for a in db.q("SELECT * FROM apps")}
    services = sorted(set(apps) | {s for e in svc_edges for s in e})
    open_inc = db.q("SELECT id, entity, action, kind FROM incidents WHERE status NOT IN ('resolved','rejected','closed')")

    def problem_for(name: str):
        for i in open_inc:
            a = i["action"] or {}
            ps = a.get("params", {}) if isinstance(a, dict) else {}
            if name in (i["entity"], ps.get("service"), ps.get("instance")):
                return i["id"]
        return None

    nodes = []
    metrics = dict(zip(services, await asyncio.gather(*(_inst_metrics(s) for s in services))))
    for s in services:
        im = metrics[s]
        rps = sum(v["rps"] for v in im.values())
        err = sum(v["rps"] * v["error_rate"] for v in im.values()) / rps if rps else None
        p95s = [v["p95_ms"] for v in im.values() if v["p95_ms"] is not None]
        a = apps.get(s, {})
        insts = [{"id": i, **v, "problem_id": problem_for(i)} for i, v in sorted(im.items())] if len(im) > 1 else []
        nodes.append({"id": s, "kind": a.get("kind") or "service", "owner": a.get("owner") or a.get("team"),
                      "rps": round(rps, 3) if im else None, "error_rate": round(err, 4) if err is not None else None,
                      "p95_ms": max(p95s) if p95s else None, "instances": insts, "problem_id": problem_for(s),
                      "connected": s in apps})

    def edge_list(counter: Counter, key_rps):
        incoming = Counter()
        for (a, b), c in counter.items():
            incoming[b] += c
        out = []
        for (a, b), c in counter.items():
            share = c / incoming[b] if incoming[b] else 0
            r, e = key_rps(b)
            out.append({"from": a, "to": b, "samples": c, "share": round(share, 3),
                        "rps": round(share * r, 3) if r is not None else None, "error_rate": e})
        return out

    node_by_id = {n["id"]: n for n in nodes}
    edges = edge_list(svc_edges, lambda b: (node_by_id.get(b, {}).get("rps"), node_by_id.get(b, {}).get("error_rate")))
    inst_metric = {i: v for s in services for i, v in metrics[s].items()}
    multi = {n["id"] for n in nodes if n["instances"]}
    iedges = [e for e in edge_list(inst_edges, lambda b: (inst_metric.get(b, {}).get("rps"),
                                                          inst_metric.get(b, {}).get("error_rate")))
              if inst_of.get(e["to"]) in multi or inst_of.get(e["from"]) in multi]
    for e in iedges:
        e["from_service"], e["to_service"] = inst_of.get(e["from"]), inst_of.get(e["to"])

    hosts = [{"name": h["name"], "address": h["address"]} for h in db.q("SELECT name, address FROM hosts")]
    data = {"nodes": nodes, "edges": edges, "instance_edges": iedges, "entry": [r for r, _ in roots.most_common()],
            "traces_sampled": len([s for s in spans_all if s]), "hosts": hosts, "ts": time.time()}
    _cache.update(ts=time.time(), data=data)
    return data
