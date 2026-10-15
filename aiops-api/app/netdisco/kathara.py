"""Network discovery for NIKA labs (sands-lab, SIGCOMM NGNO 2025), which run on Kathara.

NIKA's routers do not run SNMP or LLDP, so this source reads the same facts another way, without changing the lab:

  topology  Kathara's collision domains: every container port carries `kathara.link` (the link it is cabled to) and
            `kathara.iface` (its ethN). Two ports on one collision domain are one cable. This IS the research's
            topology definition, not something inferred.
  state     inside each node: `ip -o -4 addr`, `ip -o link` (port up/down), and FRR's `show bgp summary json`
  roles     the node's image (NIKA's FRR image = router) and what runs on it (bind = dns, an HTTP server = web)

The result is the same `snmp.Device` / endpoints shape the SNMP source produces, so topology.build is unchanged.
"""
from __future__ import annotations

import ipaddress
import json
import re

from .snmp import ArpEntry, Device, Neighbor, Port

LABEL = "app=kathara"
PROBE = ("ip -o -4 addr; echo '##'; ip -o link; echo '##'; "
         "pgrep -x named >/dev/null && echo svc=dns; pgrep -f '[h]ttp.server|[n]ginx' >/dev/null && echo svc=web; "
         "echo '##'; command -v vtysh >/dev/null && (vtysh -c 'show bgp summary json' 2>/dev/null || echo BGP_DOWN)")


def parse_probe(text: str) -> dict:
    """Output of PROBE -> {"ports": {eth: {"ips", "up", "mac"}}, "services": [...], "router": bool, "bgp": {...}}"""
    parts = (text.split("##") + ["", "", "", ""])[:4]
    addr, link, svc, bgp = parts
    ports: dict[str, dict] = {}
    for line in link.splitlines():
        m = re.match(r"\s*\d+:\s+([\w.-]+)(?:@\S+)?:\s+<([^>]*)>.*?state (\w+)", line)
        if not m or m.group(1) == "lo":
            continue
        flags, state = m.group(2).split(","), m.group(3)
        mac = re.search(r"link/ether ([0-9a-f:]{17})", line)
        ports[m.group(1)] = {"up": "UP" in flags and "LOWER_UP" in flags and state != "DOWN",
                             "mac": mac.group(1) if mac else "", "ips": []}
    for line in addr.splitlines():
        m = re.match(r"\s*\d+:\s+([\w.-]+)\s+inet\s+([\d./]+)", line)
        if m and m.group(1) in ports:
            ports[m.group(1)]["ips"].append(m.group(2))
    services = sorted({l.split("=", 1)[1] for l in svc.split() if l.startswith("svc=")})
    out = {"ports": ports, "services": services, "router": False, "bgp": None}
    bgp = bgp.strip()
    if bgp:
        out["router"] = True
        if "BGP_DOWN" in bgp:
            out["bgp"] = {"ok": False, "peers": {}}
        else:
            try:
                peers = (json.loads(bgp).get("ipv4Unicast") or {}).get("peers") or {}
                out["bgp"] = {"ok": any(p.get("state") == "Established" for p in peers.values()),
                              "peers": {ip: {"name": p.get("hostname", ""), "state": p.get("state", "")} for ip, p in peers.items()}}
            except (ValueError, AttributeError):
                out["bgp"] = {"ok": False, "peers": {}}
    return out


def build(nodes: list[dict]) -> tuple[list[Device], dict[str, dict]]:
    """nodes: [{"name", "image", "links": {ethN: link_name}, "probe": parse_probe(...)}] for one lab.
    Routers become polled devices; everything else becomes an endpoint the routers see on a port."""
    members: dict[str, list[tuple[str, str]]] = {}          # link -> [(node, eth)]
    for n in nodes:
        for eth, link in n["links"].items():
            members.setdefault(link, []).append((n["name"], eth))
    by = {n["name"]: n for n in nodes}
    is_router = {n["name"]: n["probe"]["router"] or "frr" in (n.get("image") or "") for n in nodes}

    devices, endpoints = [], {}
    for n in nodes:
        if is_router[n["name"]]:
            continue
        for eth, p in n["probe"]["ports"].items():
            for ip in p["ips"]:
                endpoints[ip.split("/")[0]] = {"name": n["name"], "kind": "nika", "services": n["probe"]["services"],
                                               "link_up": p["up"], "stable_name": True}
    for n in nodes:
        name = n["name"]
        if not is_router[name]:
            continue
        bgp = n["probe"].get("bgp") or {"ok": True, "peers": {}}
        d = Device(address=f"kathara:{name}", name=name, descr=f"NIKA lab router ({n.get('image') or 'FRR'})",
                   routing_ok=bgp["ok"], bgp_peers=bgp["peers"])
        for i, (eth, p) in enumerate(sorted(n["probe"]["ports"].items()), start=1):
            d.ports[i] = Port(i, eth, mac=p["mac"], up=p["up"],
                              ips=[ipaddress.ip_interface(x) for x in p["ips"]])
        for eth, link in n["links"].items():
            for other, oeth in members.get(link, []):
                if other == name:
                    continue
                if is_router[other]:
                    d.neighbors.append(Neighbor(eth, other, oeth))
                else:
                    op = by[other]["probe"]["ports"].get(oeth) or {}
                    for ip in op.get("ips", []):
                        d.arp.append(ArpEntry(eth, ip.split("/")[0], op.get("mac", "")))
        devices.append(d)
    return devices, endpoints


# ---------------- reading the running lab (Docker) ----------------
def _links_of(container) -> dict[str, str]:
    out = {}
    for net in (container.attrs.get("NetworkSettings", {}).get("Networks") or {}).values():
        opts = net.get("DriverOpts") or {}
        if "kathara.iface" in opts and "kathara.link" in opts:
            out[f"eth{opts['kathara.iface']}"] = opts["kathara.link"]
    return out


def snapshot(client) -> tuple[list[Device], dict[str, dict]]:
    """All Kathara labs running on this Docker host, read in place. Empty when there are none."""
    nodes = []
    for c in client.containers.list(filters={"label": LABEL}):
        labels = c.labels or {}
        try:
            code, out = c.exec_run(["sh", "-c", PROBE], demux=False)
            text = (out or b"").decode(errors="replace")
        except Exception:
            text = ""
        nodes.append({"name": labels.get("name") or c.name, "image": labels.get("io.nika.image") or "",
                      "links": _links_of(c), "probe": parse_probe(text)})
    return build(nodes) if nodes else ([], {})
