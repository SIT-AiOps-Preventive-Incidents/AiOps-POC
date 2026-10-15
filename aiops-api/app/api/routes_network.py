"""/api/v1/network: discovered network assets, the layered topology, and what changed."""
from fastapi import APIRouter

from .. import netseg
from ..netdisco import nika, service

router = APIRouter(prefix="/api/v1/network", tags=["network"])


@router.get("", summary="Topology: devices, hosts and services, with the links between them")
async def get_topology():
    topo = await service.current()
    return {**topo, "events": service.events(30), "lab": await nika.status()}


@router.post("/scans", status_code=201, summary="Run discovery now")
async def scan_now():
    topo = await service.scan()
    return {**topo, "events": service.events(30), "lab": await nika.status()}


@router.get("/events", summary="Network changes: links, devices, new and unknown hosts")
async def get_events(limit: int = 100):
    return service.events(min(limit, 500))


@router.get("/discovered", summary="Your network: what connected servers hear on their own segments, grouped")
async def discovered(view: str = "network"):
    view = view if view in ("network", "service", "org") else "network"
    segments, neighbors, hosts = netseg.load()
    groups = netseg.views(view, segments, neighbors, hosts)
    machines = {i["ip"] for g in groups for i in g["items"]}
    return {"view": view, "segments": segments, "groups": groups,
            "summary": {"segments": len({s["cidr"] for s in segments}), "machines": len(machines),
                        "listening_on": sorted({s["host"] for s in segments})}}
