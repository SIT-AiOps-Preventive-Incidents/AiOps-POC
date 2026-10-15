"""Topology: SNMP snapshots of the network devices -> one layered graph, from the core down to the services.

  layer 0  core     devices whose ports lead only to other devices
  layer 1  access   devices that have hosts on a port (seen in their ARP table)
  layer 2  host     every address an access device sees on a host port, named from what AIOps One knows about it
  layer 3  service  the services running on that host (from the service registry)

Pure: same input, same output. The caller keeps `known` (what earlier scans saw) so that a cable whose LLDP entry
has expired still shows, as down, and so that changes between two scans become events.
"""
from __future__ import annotations

import ipaddress
from collections import deque

from .snmp import Device, is_port

MISSING_KEEP_S = 24 * 3600     # a host that stopped showing up stays on the map (as missing) for a day
NEW_FOR_S = 15 * 60            # "new" badge on assets first seen in the last 15 minutes


def _link_id(a: str, ap: str, b: str, bp: str) -> str:
    return "--".join(sorted([f"{a}:{ap}", f"{b}:{bp}"]))


def _remote_port(dev: Device | None, port_id: str, descr: str) -> str:
    """LLDP port id may be a name or a MAC; return the remote device's port name when we can resolve it."""
    if dev:
        for p in dev.ports.values():
            if p.name in (port_id, descr) or (p.mac and p.mac == port_id.lower()):
                return p.name
    return descr or port_id


def build(devices: list[Device], endpoints: dict[str, dict], known: dict | None = None, now: float = 0.0) -> dict:
    """devices: polled snapshots.  endpoints: {ip: {"name", "kind", "services": [..]}} for addresses AIOps One knows.
    known: {"assets": {id: {...first_seen, last_seen, status}}, "links": {id: {...}}} from earlier scans."""
    known = known or {"assets": {}, "links": {}}
    by_name = {d.name: d for d in devices}
    device_ips = {str(i.ip) for d in devices for p in d.ports.values() for i in p.ips} | {d.address for d in devices}
    nodes: dict[str, dict] = {}
    links: dict[str, dict] = {}

    # ---- devices and the cables between them (LLDP) ----
    for d in devices:
        nodes[f"dev:{d.name}"] = {
            "id": f"dev:{d.name}", "kind": "device", "name": d.name, "role": "core", "layer": 0,
            "status": ("up" if d.routing_ok else "routing down") if d.reachable else "unreachable",
            "ip": d.address, "bgp_peers": d.bgp_peers, "descr": d.descr.split("\n")[0][:120],
            "uptime_s": d.uptime_s, "error": d.error,
            "ports": [{"name": p.name, "up": p.up, "mac": p.mac, "speed_mbps": p.speed_mbps,
                       "ips": [str(i) for i in p.ips], "mgmt": p.name == d.mgmt_port}
                      for p in sorted(d.ports.values(), key=lambda p: p.index) if is_port(p)]}
    for d in devices:
        for n in d.neighbors:
            peer = by_name.get(n.system)
            rport = _remote_port(peer, n.remote_port, n.remote_descr)
            lid = _link_id(d.name, n.port, n.system, rport)
            if n.system not in by_name and f"dev:{n.system}" not in nodes:   # heard over LLDP but not polled
                nodes[f"dev:{n.system}"] = {"id": f"dev:{n.system}", "kind": "device", "name": n.system, "role": "core",
                                            "layer": 0, "status": "not polled", "ip": "", "descr": "", "ports": []}
            links[lid] = {"id": lid, "kind": "cable", "a": f"dev:{d.name}", "a_port": n.port,
                          "b": f"dev:{n.system}", "b_port": rport, "status": "up"}
    for lid, old in known.get("links", {}).items():    # a cable we saw before but whose LLDP entry is gone
        if (old.get("kind") == "cable" and lid not in links and old["a"] in nodes and old["b"] in nodes
                and old["a"] != old["b"]):
            links[lid] = {**{k: old[k] for k in ("id", "kind", "a", "a_port", "b", "b_port")}, "status": "down"}
    for lk in links.values():                           # a port that is down takes its cable down
        for end, port in (("a", "a_port"), ("b", "b_port")):
            dev = by_name.get(lk[end][4:])
            p = dev.port_by_name(lk[port]) if dev and dev.reachable else None
            if dev and not dev.reachable:
                lk["status"] = "down"
            elif p is not None and not p.up:
                lk["status"] = "down"

    # ---- hosts: addresses an access device sees on a non-management port ----
    seen_hosts = set()
    for d in devices:
        mgmt = d.mgmt_port
        for e in d.arp:
            if e.port == mgmt or e.ip in device_ips or not _in_port_subnet(d, e.port, e.ip):
                continue
            nodes[f"dev:{d.name}"].update(role="access", layer=1)
            ep = endpoints.get(e.ip) or {}
            # a host is its MAC, unless the source names it for good (NIKA nodes get a new MAC on every redeploy)
            hid = f"host:{ep['name']}" if ep.get("stable_name") else f"host:{e.mac}"
            port = d.port_by_name(e.port)
            seen_hosts.add(hid)
            up = (port is None or port.up) and ep.get("link_up", True)   # either end of the cable can be down
            nodes[hid] = {"id": hid, "kind": "host", "name": ep.get("name") or f"unknown {e.ip}", "layer": 2,
                          "ip": e.ip, "mac": e.mac, "known": bool(ep), "host_kind": ep.get("kind", ""),
                          "attached": f"{d.name}:{e.port}", "status": "up" if up else "down"}
            links[f"{hid}--dev:{d.name}"] = {"id": f"{hid}--dev:{d.name}", "kind": "access", "a": f"dev:{d.name}",
                                            "a_port": e.port, "b": hid, "b_port": "", "status": nodes[hid]["status"]}
            for s in ep.get("services") or []:
                sid = f"svc:{s}"
                nodes.setdefault(sid, {"id": sid, "kind": "service", "name": s, "layer": 3, "status": "up"})
                links[f"{hid}--{sid}"] = {"id": f"{hid}--{sid}", "kind": "runs", "a": hid, "a_port": "", "b": sid,
                                          "b_port": "", "status": "up"}
    for aid, old in known.get("assets", {}).items():   # hosts that stopped answering
        if old.get("kind") == "host" and aid not in seen_hosts and now - (old.get("last_seen") or 0) < MISSING_KEEP_S:
            nodes[aid] = {**{k: old.get(k) for k in ("id", "kind", "name", "layer", "ip", "mac", "known", "attached")},
                          "status": "missing"}

    _mark_cut_off(nodes, links)
    for n in nodes.values():
        k = known.get("assets", {}).get(n["id"]) or {}
        n["first_seen"] = k.get("first_seen") or now
        n["last_seen"] = now if n["status"] not in ("missing",) else k.get("last_seen")
        # new = appeared after the first scan (the first scan is the baseline), and not long ago
        n["new"] = bool(known.get("assets")) and (not k or bool(k.get("new"))) and now - n["first_seen"] < NEW_FOR_S
    return {"nodes": sorted(nodes.values(), key=lambda n: (n["layer"], n["name"])),
            "links": sorted(links.values(), key=lambda l: l["id"]), "ts": now,
            "events": diff(known, nodes, links, now)}


def _in_port_subnet(d: Device, port: str, ip: str) -> bool:
    p = d.port_by_name(port)
    if p is None or not p.ips:
        return True
    try:
        return any(ipaddress.ip_address(ip) in i.network for i in p.ips)
    except ValueError:
        return False


def _mark_cut_off(nodes: dict, links: dict) -> None:
    """Walk from the core over working links. Whatever is not reached is cut off, and so are the services on it."""
    adj: dict[str, list[str]] = {}
    for lk in links.values():
        if lk["status"] == "up":
            adj.setdefault(lk["a"], []).append(lk["b"])
            adj.setdefault(lk["b"], []).append(lk["a"])
    cores = [n for n in nodes.values() if n["kind"] == "device" and n["role"] == "core"]
    start = [n["id"] for n in cores if n["status"] == "up"]
    if not cores:   # no core at all (a flat network): every working device is a starting point
        start = [n["id"] for n in nodes.values() if n["kind"] == "device" and n["status"] == "up"]
    reached, q = set(start), deque(start)
    blocked = {n["id"] for n in nodes.values() if n["status"] in ("routing down", "unreachable", "down")}
    while q:
        cur = q.popleft()
        if cur in blocked:      # reached, but it does not pass traffic on
            continue
        for nb in adj.get(cur, []):
            if nb not in reached:
                reached.add(nb)
                q.append(nb)
    for n in nodes.values():
        n["reachable"] = n["id"] in reached and n["id"] not in blocked
        if not n["reachable"] and n["status"] == "up":
            n["status"] = "cut off"


def impacted_services(topo: dict) -> list[str]:
    return sorted(n["name"] for n in topo["nodes"] if n["kind"] == "service" and not n["reachable"])


def diff(known: dict, nodes: dict, links: dict, now: float) -> list[dict]:
    """What changed since the last scan, as events. Nothing is reported on the very first scan (no baseline yet)."""
    old_a, old_l = known.get("assets", {}), known.get("links", {})
    if not old_a:
        return []
    ev = []

    def add(kind, severity, entity, text):
        ev.append({"ts": now, "kind": kind, "severity": severity, "entity": entity, "text": text})

    for lid, lk in links.items():
        was = (old_l.get(lid) or {}).get("status")
        if lk["kind"] == "access" or was is None:
            continue
        if was == "up" and lk["status"] == "down":
            add("link_down", "critical", lid, f"Link {lk['a'][4:]}:{lk['a_port']} - {lk['b'][4:]}:{lk['b_port']} went down")
        elif was == "down" and lk["status"] == "up":
            add("link_up", "info", lid, f"Link {lk['a'][4:]}:{lk['a_port']} - {lk['b'][4:]}:{lk['b_port']} is back up")
    for nid, n in nodes.items():
        was = (old_a.get(nid) or {}).get("status")
        if n["kind"] == "device":
            if was == "up" and n["status"] == "unreachable":
                add("device_down", "critical", nid, f"{n['name']} stopped answering SNMP")
            elif was == "up" and n["status"] == "routing down":
                add("routing_down", "critical", nid, f"{n['name']} lost its routing (no BGP session established)")
            elif was == "routing down" and n["status"] == "up":
                add("routing_up", "info", nid, f"{n['name']} is routing again")
            elif was == "unreachable" and n["status"] == "up":
                add("device_up", "info", nid, f"{n['name']} answers again")
        elif n["kind"] == "host":
            if was is None:
                if n.get("known"):
                    add("host_new", "info", nid, f"New host {n['name']} ({n['ip']}) on {n.get('attached')}")
                else:
                    add("host_unknown", "warning", nid,
                        f"Unknown device {n['ip']} ({n['mac']}) appeared on {n.get('attached')}: not a host AIOps One knows")
            elif was != "missing" and n["status"] == "missing":
                add("host_missing", "warning", nid, f"{n['name']} ({n['ip']}) is no longer seen on the network")
            elif was in ("up",) and n["status"] in ("cut off", "down"):
                add("host_cut_off", "critical", nid, f"{n['name']} lost its path to the core")
            elif was in ("cut off", "down") and n["status"] == "up":
                add("host_reconnected", "info", nid, f"{n['name']} is reachable again")
    return ev
