"""Add every app that is sending telemetry, without anyone pressing "Add".

Connecting a server already ships its apps' traces and logs; asking the user to register each name again was a
step with no decision in it. Every minute, any service name with traffic (traces) or log lines in the last 15
minutes that RadarOps does not know yet is added, on the computer its logs came from, owned by that computer's
team. Only fresh data counts: Prometheus keeps a stopped app's counters (rate 0) and Loki's label list answers
from whole index buckets, which is how apps that went quiet days ago used to show up as "sending data".
"""
from __future__ import annotations

import asyncio
import logging
import time

import httpx

from . import repo
from . import telemetry as tm

WINDOW = "15m"
EVERY_S = 60
IGNORE = {"aiops-agent", "unknown_service"}   # the agent's own logs, and spans from apps that never set a name


def pick_new(traces: dict[str, float], logs: dict[str, str | None], known: set[str]) -> list[dict]:
    """Names with fresh data that nobody registered: [{service_name, rps, host}], sorted by name.
    traces = name -> req/s over the window (0 = only stale counters); logs = name -> host the lines came from."""
    names = {n for n, r in traces.items() if r and r > 0} | set(logs)
    return [{"service_name": n, "rps": round(traces[n], 3) if traces.get(n) else None, "host": logs.get(n)}
            for n in sorted(names) if n and n not in known and n not in IGNORE]


async def fresh() -> tuple[dict[str, float], dict[str, str | None]]:
    traces = {}
    for r in await tm.prom(f'sum by (service_name) (rate({tm.CALLS}{{{tm.SRV}}}[{WINDOW}]))'):
        if r["metric"].get("service_name"):
            traces[r["metric"]["service_name"]] = float(r["value"][1])
    logs: dict[str, str | None] = {}
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            res = (await c.get(f"{tm.LOKI}/loki/api/v1/query", params={
                "query": f'sum by (service_name, host_name) (count_over_time({{service_name=~".+"}}[{WINDOW}]))',
                "time": int(time.time() * 1e9)})).json().get("data", {}).get("result", [])
        for r in res:
            n = r["metric"].get("service_name")
            if n and float(r["value"][1]) > 0:
                logs[n] = logs.get(n) or r["metric"].get("host_name") or None
    except Exception:
        pass
    return traces, logs


def known() -> set[str]:
    return {s["service_name"] for s in repo.list_services(("service", "network", "process", "external"))}


async def pending() -> list[dict]:
    return pick_new(*(await fresh()), known())


async def sweep() -> list[str]:
    added = []
    for c in await pending():
        name, host = c["service_name"], c["host"]
        h = repo.host(host) if host else None
        repo.create_service(name, display_name=name.replace("-", " ").replace("_", " ").title(), kind="service",
                            source="traced" if c["rps"] else "discovered", owner=(h or {}).get("owner") or "unassigned")
        if h:
            repo.ensure_instance(name, f"{host}:{name}", host=host)
        added.append(name)
    if added:
        logging.info("auto-added services: %s", ", ".join(added))
    return added


async def loop():
    while True:
        try:
            await sweep()
        except Exception:
            logging.exception("auto-add sweep failed")
        await asyncio.sleep(EVERY_S)
