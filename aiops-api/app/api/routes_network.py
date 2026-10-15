"""/api/v1/network: discovered network assets, the layered topology, and what changed."""
from fastapi import APIRouter

from .. import netseg
from ..netdisco import service

router = APIRouter(prefix="/api/v1/network", tags=["network"])


@router.get("", summary="Topology: devices, hosts and services, with the links between them")
async def get_topology():
    topo = await service.current()
    return {**topo, "events": service.events(30)}


@router.post("/scans", status_code=201, summary="Run discovery now")
async def scan_now():
    topo = await service.scan()
    return {**topo, "events": service.events(30)}


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


@router.get("/recommendations", summary="Which discovered-but-unmonitored machines to connect first, and why")
async def recommendations():
    from .. import fleet, health, netseg
    segments, neighbors, hosts = netseg.load()
    problem_hosts = {h["name"] for h in await health.hosts_health() if h["status"] in ("problem", "down")}
    recs = fleet.recommend(segments, neighbors, hosts, problem_hosts)
    return {"count": len(recs), "recommendations": recs[:20]}


@router.get("/graph", summary="3D topology: internet, gateways, network hubs, machines and the services on them")
async def topology_graph():
    from .. import health, repo
    segments, neighbors, base = netseg.load()
    live = {h["name"]: h["status"] for h in await health.hosts_health()}
    for h in base:
        h["status"] = live.get(h["name"])
    svc = {s["service"]: s["status"] for s in await health.services_health()}
    return netseg.graph(segments, neighbors, base, svc, repo.discovered_edges(3600))
