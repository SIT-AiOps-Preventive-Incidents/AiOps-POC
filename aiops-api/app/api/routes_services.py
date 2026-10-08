"""/api/v1/services - applications AIOps watches (traced, network devices, discovered processes)."""
import time

import httpx
from fastapi import APIRouter, Response

from .. import health, repo
from .. import telemetry as tm
from .errors import ApiError, not_found
from .schemas import ServiceIn, ServicePatch

router = APIRouter(prefix="/api/v1/services", tags=["services"])


@router.get("", summary="List services with live health")
async def list_services(kind: str | None = None):
    kinds = tuple(kind.split(",")) if kind else ("service", "network", "process", "external")
    return await health.services_health(kinds)


@router.post("", status_code=201, summary="Register a service")
async def create_service(body: ServiceIn, response: Response):
    if repo.service(body.service_name):
        raise ApiError(409, f"service '{body.service_name}' already exists")
    s = repo.create_service(body.service_name, display_name=body.display_name or body.service_name.replace("-", " ").title(),
                            kind="service", source="manual", language=body.language, owner=body.owner or "unassigned",
                            repo=body.repo, environment=body.environment, entry_url=body.entry_url,
                            entry_method=body.entry_method)
    s = repo.update_service(s["service_name"], instrumentation="sdk")  # the "Connect a service" wizard = SDK setup
    response.headers["Location"] = f"/api/v1/services/{s['service_name']}"
    return s


@router.get("/discovered", summary="Telemetry that is arriving from services nobody registered yet")
async def discovered():
    known = {s["service_name"] for s in repo.list_services(("service", "network", "process", "external"))}
    seen: dict[str, float | None] = {}
    for r in await tm.prom(f'sum by (service_name) (rate({tm.CALLS}{{span_kind="SPAN_KIND_SERVER"}}[15m]))'):
        if r["metric"].get("service_name"):
            seen[r["metric"]["service_name"]] = round(float(r["value"][1]), 3)
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            vals = (await c.get(f"{tm.LOKI}/loki/api/v1/label/service_name/values",
                                params={"start": int((time.time() - 900) * 1e9)})).json().get("data", [])
        for n in vals:
            seen.setdefault(n, None)
    except Exception:
        pass
    return [{"service_name": n, "rps": r} for n, r in sorted(seen.items())
            if n not in known and n not in ("aiops-agent", "unknown_service")]


@router.get("/{name}", summary="Service detail: health, charts, endpoints, versions, traces, logs")
async def get_service(name: str):
    s = repo.service(name)
    if not s:
        raise not_found("service", name)
    series = {}
    for m in ("rps", "error_rate", "p95"):
        r = await tm.prom_range(tm.svc_expr(name, m), minutes=60, step=30)
        series[m] = r[0]["points"] if r else []
    sel = f'service_name="{name}",{tm.SRV}'
    eps = await tm.prom(f"sum by (span_name) (rate({tm.CALLS}{{{sel}}}[5m]))")
    eperr = await tm.prom(f'sum by (span_name) (rate({tm.CALLS}{{{sel},status_code="STATUS_CODE_ERROR"}}[5m]))')
    emap = {e["metric"].get("span_name"): float(e["value"][1]) for e in eperr}
    endpoints = [{"name": e["metric"].get("span_name"), "rps": round(float(e["value"][1]), 3),
                  "error_rate": round(emap.get(e["metric"].get("span_name"), 0) / float(e["value"][1]), 4)
                  if float(e["value"][1]) else 0} for e in eps]
    return {"service": s, "health": await health.service_health(s), "series": series, "endpoints": endpoints,
            "versions": await tm.error_rate_by_version(name, "5m"), "deployments": repo.deployments(name, limit=15),
            "logs": await tm.loki_logs(f'{{service_name="{name}"}}', minutes=15, limit=40),
            "traces": await tm.tempo_search(f'{{ resource.service.name = "{name}" }}', minutes=15, limit=15),
            "incidents": [i for i in repo.list_incidents(limit=200) if i["entity"] == name][:10]}


@router.patch("/{name}", summary="Update owner, language, entry point ...")
async def patch_service(name: str, body: ServicePatch):
    if not repo.service(name):
        raise not_found("service", name)
    return repo.update_service(name, **body.model_dump(exclude_none=True))


@router.delete("/{name}", status_code=204, summary="Stop watching a service")
async def delete_service(name: str):
    if not repo.delete_service(name):
        raise not_found("service", name)
    return Response(status_code=204)


@router.get("/{name}/telemetry", summary="Is the service sending metrics, logs and traces?")
async def telemetry_status(name: str):
    rps = await tm.prom_value(tm.svc_expr(name, "rps", "5m"))
    logs = await tm.loki_count(f'sum(count_over_time({{service_name="{name}"}}[5m]))')
    traces = await tm.tempo_search(f'{{ resource.service.name = "{name}" }}', minutes=5, limit=1)
    return {"service": name, "metrics": bool(rps), "logs": logs > 0, "traces": bool(traces), "rps": rps,
            "log_lines_5m": logs}
