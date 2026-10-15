"""Outside-in checks for systems nothing can be installed on.

Every CHECK_S seconds AIOps calls the system's web address, the way a user's browser would, and records each call
as an OpenTelemetry trace (plus one log line) under that service's name. The traces go through the same collector
as everything else, so request rate, errors and response time, the learned normal range, the detector, the AI
investigation and the service page all work for the system without touching it.

Only a reply of 500 or above, or no reply at all, counts as an error: a login page or a 404 still means the system
is up. The certificate is verified like a browser would; an invalid certificate is a failed check.
"""
import asyncio
import os
import ssl
import time
import traceback
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

from . import repo

CHECK_S = 10
TIMEOUT_S = 8
OTLP = os.environ.get("OTLP_INTERNAL_URL", "http://otel-collector:4318")
KIND = "check"          # services.instrumentation for systems watched from the outside
_last: dict[str, list[dict]] = {}
_cert: dict[str, tuple[float, int | None]] = {}


def valid_url(url: str) -> bool:
    try:
        u = urlsplit(url.strip())
    except ValueError:
        return False
    return u.scheme in ("http", "https") and bool(u.hostname)


def outcome(status: int | None, error: str | None) -> tuple[str, str | None]:
    if error:
        return "error", error
    if status is None or status >= 500:
        return "error", f"HTTP {status}"
    return "ok", None


def _attr(k: str, v) -> dict:
    if isinstance(v, bool):
        return {"key": k, "value": {"boolValue": v}}
    if isinstance(v, int):
        return {"key": k, "value": {"intValue": v}}
    return {"key": k, "value": {"stringValue": str(v)}}


def to_otlp(service: str, res: dict, trace_id: str, span_id: str) -> dict:
    """One check as one SERVER span of the checked service (OTLP/JSON)."""
    start = int(res["start"] * 1e9)
    state, why = outcome(res["status"], res["error"])
    path = urlsplit(res["url"]).path or "/"
    attrs = [_attr("http.request.method", "GET"), _attr("url.full", res["url"]), _attr("aiops.check", "outside-in")]
    if res["status"] is not None:
        attrs.append(_attr("http.response.status_code", res["status"]))
    if res.get("cert_days_left") is not None:
        attrs.append(_attr("tls.certificate.days_left", res["cert_days_left"]))
    return {"resourceSpans": [{
        "resource": {"attributes": [_attr("service.name", service), _attr("telemetry.source", "aiops-outside-in-check")]},
        "scopeSpans": [{"scope": {"name": "aiops.synthetic"}, "spans": [{
            "traceId": trace_id, "spanId": span_id, "name": f"GET {path}", "kind": 2,
            "startTimeUnixNano": str(start), "endTimeUnixNano": str(start + round(res["ms"] * 1e6)),
            "attributes": attrs, "status": {"code": 2, "message": why} if state == "error" else {}}]}]}]}


def log_line(res: dict) -> str:
    ms = round(res["ms"])
    if res["status"] is None:
        return f"GET {res['url']} failed after {ms} ms: {res['error']}"
    line = f"GET {res['url']} -> {res['status']} in {ms} ms"
    if res.get("final_url") and res["final_url"] != res["url"]:
        line += f" (ended at {res['final_url']})"
    if res.get("cert_days_left") is not None:
        line += f" · certificate valid {res['cert_days_left']} more days"
    return line


def _log_otlp(service: str, res: dict, trace_id: str, span_id: str) -> dict:
    state, _ = outcome(res["status"], res["error"])
    return {"resourceLogs": [{
        "resource": {"attributes": [_attr("service.name", service)]},
        "scopeLogs": [{"scope": {"name": "aiops.synthetic"}, "logRecords": [{
            "timeUnixNano": str(int(res["start"] * 1e9)), "severityText": "ERROR" if state == "error" else "INFO",
            "severityNumber": 17 if state == "error" else 9, "body": {"stringValue": log_line(res)},
            "traceId": trace_id, "spanId": span_id}]}]}]}


async def _cert_days(url: str) -> int | None:
    """Days until the server certificate expires (verified like a browser), re-read once an hour."""
    u = urlsplit(url)
    if u.scheme != "https":
        return None
    key = f"{u.hostname}:{u.port or 443}"
    hit = _cert.get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    days = None
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection(u.hostname, u.port or 443, ssl=ssl.create_default_context()),
                                      TIMEOUT_S)
        cert = w.get_extra_info("peercert")
        w.close()
        end = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), timezone.utc)
        days = (end - datetime.now(timezone.utc)).days
    except Exception:
        pass
    _cert[key] = (time.time(), days)
    return days


async def probe(url: str) -> dict:
    res = {"url": url, "status": None, "error": None, "start": time.time(), "ms": 0.0, "final_url": None,
           "cert_days_left": None}
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S, follow_redirects=True,
                                     headers={"User-Agent": "AIOps-One-check/1.0"}) as c:
            r = await c.get(url)
        res.update(status=r.status_code, final_url=str(r.url))
    except Exception as e:
        res["error"] = type(e).__name__
    res["ms"] = round((time.perf_counter() - t0) * 1000, 1)
    res["cert_days_left"] = await _cert_days(url)
    return res


async def check(service: str, url: str) -> dict:
    """Call the URL once, ship the trace + log, remember the result."""
    res = await probe(url)
    tid, sid = os.urandom(16).hex(), os.urandom(8).hex()
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{OTLP}/v1/traces", json=to_otlp(service, res, tid, sid))
            await c.post(f"{OTLP}/v1/logs", json=_log_otlp(service, res, tid, sid))
    except Exception:
        traceback.print_exc()
    res.update(state=outcome(res["status"], res["error"])[0], trace_id=tid)
    hist = _last.setdefault(service, [])
    hist.insert(0, res)
    del hist[20:]
    return res


def recent(service: str) -> list[dict]:
    return _last.get(service, [])


def watched() -> list[dict]:
    return [s for s in repo.list_services(("service",)) if s.get("instrumentation") == KIND and s.get("entry_url")]


async def loop():
    await asyncio.sleep(5)
    while True:
        try:
            await asyncio.gather(*(check(s["service_name"], s["entry_url"]) for s in watched()))
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(CHECK_S)
