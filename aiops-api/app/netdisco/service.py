"""Discovery loop: find the devices, poll them, build the topology, remember it, record what changed.

Devices come from two places, so nothing has to be typed in for the lab and real gear still works:
  * containers labelled aiops.netdevice=true (the demo network lab)
  * the "net_devices" setting: comma-separated addresses of real switches/routers
Everything else AIOps One already knows (containers, hosts, services) is used to name what the switches see.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time

from .. import db, repo
from .. import telemetry as tm
from . import snmp, topology

log = logging.getLogger("netdisco")
SCAN_S = int(os.environ.get("NET_SCAN_S", "60"))
LABEL = "aiops.netdevice"
_state = {"topo": None, "scanning": False}


def init():
    with open(os.path.join(os.path.dirname(__file__), "schema.sql")) as f:
        db.conn().execute(f.read())


def _labelled_devices() -> list[str]:
    try:
        return sorted(c.name for c in tm.docker_client().containers.list(filters={"label": f"{LABEL}=true"}))
    except Exception:
        return []


def device_addresses() -> list[str]:
    manual = [a.strip() for a in (db.settings().get("net_devices") or "").split(",") if a.strip()]
    return list(dict.fromkeys(_labelled_devices() + manual))


def _endpoints() -> dict[str, dict]:
    """ip -> what AIOps One calls it: containers (with their services) and registered hosts."""
    svc_of: dict[str, list[str]] = {}
    for s in repo.list_services(("service", "process")):
        for i in s.get("instances") or []:
            for key in {i.get("container"), i.get("name")} - {None}:
                svc_of.setdefault(key, []).append(s["service_name"])
    out: dict[str, dict] = {}
    for h in repo.list_hosts():
        for ip in h.get("ip_addresses") or []:
            out[ip.split("/")[0]] = {"name": h["name"], "kind": "host", "services": []}
    try:
        for c in tm.docker_client().containers.list():
            for net in (c.attrs.get("NetworkSettings", {}).get("Networks") or {}).values():
                ip = net.get("IPAddress")
                # only containers that run a service AIOps One monitors count as known; anything else a switch
                # sees is reported as an unknown device
                if ip and c.name in svc_of:
                    out[ip] = {"name": c.name, "kind": "container", "services": sorted(set(svc_of[c.name]))}
    except Exception as e:
        log.warning("docker endpoints: %s", e)
    return out


def _known() -> dict:
    assets = {r["id"]: {**r["data"], "status": r["status"], "first_seen": r["first_seen"], "last_seen": r["last_seen"]}
              for r in db.q("SELECT * FROM net_assets")}
    links = {r["id"]: {**r["data"], "status": r["status"]} for r in db.q("SELECT * FROM net_links")}
    return {"assets": assets, "links": links}


def _save(topo: dict):
    with db.tx():
        for n in topo["nodes"]:
            db.ex("""INSERT INTO net_assets(id, kind, status, data, first_seen, last_seen) VALUES (%s,%s,%s,%s,%s,%s)
                     ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, data=EXCLUDED.data,
                       last_seen=COALESCE(EXCLUDED.last_seen, net_assets.last_seen)""",
                  (n["id"], n["kind"], n["status"], db.J(n), db.T(n["first_seen"]), db.T(n.get("last_seen"))))
        for lk in topo["links"]:
            db.ex("""INSERT INTO net_links(id, status, data, last_seen) VALUES (%s,%s,%s, now())
                     ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, data=EXCLUDED.data, last_seen=now()""",
                  (lk["id"], lk["status"], db.J(lk)))
        for e in topo["events"]:
            db.ex("INSERT INTO net_events(ts, kind, severity, entity, text) VALUES (%s,%s,%s,%s,%s)",
                  (db.T(e["ts"]), e["kind"], e["severity"], e["entity"], e["text"]))


def has_sources() -> bool:
    if device_addresses():
        return True
    return False


async def scan() -> dict:
    """One full discovery pass. Returns the topology (also kept for the API)."""
    addrs = device_addresses()
    community = db.settings().get("net_snmp_community") or "public"
    devices = list(await asyncio.gather(*(snmp.poll(a, community) for a in addrs)))
    endpoints = await asyncio.to_thread(_endpoints)
    known = await asyncio.to_thread(_known)
    topo = topology.build(devices, endpoints, known, now=time.time())
    topo["impacted_services"] = topology.impacted_services(topo)
    topo["sources"] = addrs
    await asyncio.to_thread(_save, topo)
    for e in topo["events"]:
        log.info("network event %s: %s", e["kind"], e["text"])
    _state["topo"] = topo
    return topo


async def current() -> dict:
    if _state["topo"] is None:
        return await scan()
    return _state["topo"]


def events(limit: int = 100) -> list[dict]:
    return db.q("SELECT * FROM net_events ORDER BY ts DESC LIMIT %s", (limit,))


async def loop():
    init()
    while True:
        try:
            if await asyncio.to_thread(has_sources):
                await scan()
        except Exception as e:  # discovery must never take the API down
            log.warning("network scan failed: %s", e)
        await asyncio.sleep(SCAN_S)
