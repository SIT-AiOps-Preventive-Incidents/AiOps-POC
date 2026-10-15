"""/api/v1/network: discovered network assets, the layered topology, and what changed."""
from fastapi import APIRouter

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
