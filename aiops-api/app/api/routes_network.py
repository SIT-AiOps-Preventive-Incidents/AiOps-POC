"""/api/v1/network: discovered network assets, the layered topology, and what changed."""
from fastapi import APIRouter

from .. import netseg
from ..netdisco import service
from .errors import ApiError

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


@router.post("/proxmox", status_code=200, summary="Read a Proxmox hypervisor (read-only token) and match its VMs to what we found")
async def connect_proxmox(body: dict):
    from .. import db, netseg, proxmox
    url, tid, secret = (body.get("url") or "").strip(), (body.get("token_id") or "").strip(), body.get("secret") or ""
    if not (url.startswith("https://") and tid and secret):
        raise ApiError(422, "need an https url, an API token id (user@realm!name) and its secret")
    try:
        data = await proxmox.fetch(url, tid, secret, verify=body.get("verify_tls", True))
    except Exception as e:
        raise ApiError(502, f"could not read Proxmox: {type(e).__name__}: {e}")
    _, neighbors, _ = netseg.load()
    matched = sum(1 for n in neighbors if (n.get("mac") or "").lower() in data["mac_to_vm"])
    db.ex("INSERT INTO settings(key, value) VALUES ('proxmox_url', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (url,))
    db.ex("INSERT INTO settings(key, value) VALUES ('proxmox_token_id', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (tid,))
    db.ex("INSERT INTO settings(key, value) VALUES ('proxmox_secret', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (secret,))
    return {"nodes": len(data["nodes"]), "vms": len(data["vms"]), "matched_to_discovered": matched,
            "sample": [{"name": v["name"], "node": v["node"], "pool": v["pool"]} for v in data["vms"][:8]]}


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
    live = {h["name"]: h for h in await health.hosts_health()}
    for h in base:
        hh = live.get(h["name"]) or {}
        h["status"] = hh.get("status")
        h["problem_id"] = hh.get("problem_id")   # so a problem machine on the Fleet links to its incident
    svc = {s["service"]: s["status"] for s in await health.services_health()}
    return netseg.graph(segments, neighbors, base, svc, repo.discovered_edges(3600))
