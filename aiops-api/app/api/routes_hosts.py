"""/api/v1/hosts - computers and servers (pushed by the AIOps agent or pulled from node_exporter)."""
import asyncio
from fastapi import APIRouter, Response

from .. import agent, health, inventory, repo
from .. import telemetry as tm
from ..detector import PLATFORM_HOST
from .errors import ApiError, not_found
from .schemas import HostIn, HostRegistration, Inventory

router = APIRouter(prefix="/api/v1/hosts", tags=["hosts"])


def write_targets():
    """Prometheus file_sd for pull-based hosts."""
    import json
    import os
    d = os.environ.get("TARGETS_DIR", "/targets")
    data = [{"targets": [h["address"]], "labels": {"host": h["name"], "environment": h["environment"]}}
            for h in repo.list_hosts() if h["agent"] == "node_exporter"]
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, ".infra.json.tmp"), "w") as f:
        json.dump(data, f)
    os.replace(os.path.join(d, ".infra.json.tmp"), os.path.join(d, "infra.json"))


@router.get("", summary="List computers and servers with live metrics")
async def list_hosts():
    return await health.hosts_health()


@router.post("", status_code=201, summary="Add a server that runs node_exporter (pull)")
async def create_host(body: HostIn, response: Response):
    if repo.host(body.name):
        raise ApiError(409, f"host '{body.name}' already exists")
    h = repo.upsert_host(body.name, address=body.address, os=body.os, environment=body.environment,
                         agent="node_exporter", kind="server", owner=body.owner)
    write_targets()
    response.headers["Location"] = f"/api/v1/hosts/{body.name}"
    return h


@router.put("/{name}", summary="Register (or re-register) a host running the AIOps agent - idempotent")
async def register_host(name: str, body: HostRegistration):
    return repo.upsert_host(name, address="push (aiops-agent)", os=f"{body.os} {body.arch}".strip(), arch=body.arch,
                            agent="aiops-agent", kind=body.kind)


@router.post("/{name}/inventory", summary="Agent report: listening processes, containers and connections")
async def post_inventory(name: str, body: Inventory):
    try:
        out = inventory.ingest(name, body.model_dump())
    except KeyError:
        raise not_found("host", name)
    out["promoted"] = await inventory.promote_traced(out["instrument"])
    return out


@router.get("/{name}", summary="Host detail: charts, services on it, busiest processes / containers")
async def get_host(name: str):
    h = repo.host(name)
    if not h:
        raise not_found("host", name)
    metrics = ("cpu", "mem", "disk", "load")

    async def nothing():
        return None
    # everything below is independent - fetch it concurrently (container stats alone take ~2 s)
    *ranges, procs, services, host_h, containers = await asyncio.gather(
        *(tm.prom_range(tm.host_expr(name, m), minutes=60, step=30) for m in metrics),
        agent.t_getTopProcesses(name) if h["agent"] == "aiops-agent" else nothing(),
        health.services_health(), health.host_health(h),
        tm.containers(with_stats=True) if name == PLATFORM_HOST else nothing())
    series = {m: r[0]["points"] if r else [] for m, r in zip(metrics, ranges)}
    return {"host": host_h, "series": series, "processes": (procs or {}).get("processes", []),
            "services": [s for s in services if name in s["hosts"]], "containers": containers or [],
            "incidents": [i for i in repo.list_incidents(limit=200) if i["entity"] == name][:10]}


@router.delete("/{name}", status_code=204, summary="Stop watching a host")
async def delete_host(name: str):
    if not repo.delete_host(name):
        raise not_found("host", name)
    write_targets()
    return Response(status_code=204)
