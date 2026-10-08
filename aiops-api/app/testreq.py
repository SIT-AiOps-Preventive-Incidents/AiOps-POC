"""Service map "Test request": send one real request through the entry point with our own trace id,
then return the trace so the UI can replay the request hop by hop."""
import asyncio
import os
import time

import httpx

from . import repo
from . import telemetry as tm

_runs: dict[str, dict] = {}


async def start(entry: str | None = None) -> dict:
    """Fire the request; returns immediately with a test id (= trace id)."""
    svc = repo.service(entry) if entry else None
    if not svc:
        svc = next((s for s in repo.list_services(("service", "network")) if s.get("entry_url")), None)
    if not svc or not svc.get("entry_url"):
        raise LookupError("no service has an entry URL to send a test request to")
    trace_id, span_id = os.urandom(16).hex(), os.urandom(8).hex()
    run = {"id": trace_id, "entry": svc["service_name"], "url": svc["entry_url"], "method": svc["entry_method"],
           "started_at": time.time(), "status": "sent", "http_status": None, "duration_ms": None, "spans": []}
    _runs[trace_id] = run
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.request(svc["entry_method"], svc["entry_url"], json={"sku": "SKU-1", "qty": 1, "test": True},
                                headers={"traceparent": f"00-{trace_id}-{span_id}-01", "X-Forwarded-For": "198.51.100.10",
                                         "User-Agent": "aiops-test-request"})
        run.update(http_status=r.status_code, status="waiting_for_trace")
    except Exception as e:
        run.update(status="failed", error=f"{type(e).__name__}: {e}")
    run["duration_ms"] = round((time.time() - t0) * 1000, 1)
    if len(_runs) > 50:
        for k in list(_runs)[:-50]:
            _runs.pop(k, None)
    return {k: v for k, v in run.items() if not k.startswith("_")}


async def get(test_id: str) -> dict | None:
    run = _runs.get(test_id)
    if not run:
        return None
    if run["status"] == "waiting_for_trace":
        spans = await tm.tempo_trace(test_id)
        # the trace is complete once the slowest services have flushed (batch exporters flush every ~2-5 s)
        age = time.time() - run["started_at"]
        stable = spans and len(spans) == run.get("_last_count")
        run["_last_count"] = len(spans)
        if (spans and age > 7 and stable) or age > 30:
            run.update(status="complete", spans=spans)
    return {k: v for k, v in run.items() if not k.startswith("_")}
