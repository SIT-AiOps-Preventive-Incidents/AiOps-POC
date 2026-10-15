"""Your network: the machines a connected server hears on its own segment, grouped three ways.

Each agent reports its network interfaces (segment, gateway) and the neighbours its passive watcher heard over
ARP. Nothing is scanned. The MAC prefix tells what a neighbour is (a Proxmox VM, VMware, a container ...); a
neighbour whose IP belongs to a connected AIOps host becomes that host, with its owner and services.

Views
  network - one group per segment: gateway, connected hosts, then everything else by IP
  org     - one group per owner of connected hosts, and "Not connected to AIOps" for the rest
  service - one group per service: the hosts it runs on and the neighbours it talks to
"""
import ipaddress

# MAC prefix (OUI) -> (vendor, kind). Only what tells the kind of machine; the rest stays a plain "device".
OUI = {"bc:24:11": ("Proxmox", "virtual machine"), "52:54:00": ("QEMU/KVM", "virtual machine"),
       "00:50:56": ("VMware", "virtual machine"), "00:0c:29": ("VMware", "virtual machine"),
       "00:05:69": ("VMware", "virtual machine"), "00:15:5d": ("Hyper-V", "virtual machine"),
       "08:00:27": ("VirtualBox", "virtual machine"), "00:16:3e": ("Xen", "virtual machine"),
       "02:42:ac": ("Docker", "container")}
UNKNOWN = "Not connected to AIOps"
NO_SERVICE = "No known service"
ORDER = {"gateway": 0, "connected": 1}


def vendor(mac: str) -> tuple[str | None, str]:
    m = (mac or "").lower()
    if m[:8] in OUI:
        return OUI[m[:8]]
    try:
        if int(m[:2], 16) & 0x02:  # locally administered: a random or software-made address
            return None, "random MAC"
    except ValueError:
        pass
    return None, "device"


def segment_of(ip: str, segments: list[dict]) -> dict | None:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return None
    return next((s for s in segments if a in ipaddress.ip_network(s["cidr"], strict=False)), None)


def kind_of(n: dict, seg: dict | None) -> str:
    if seg and n["ip"] == seg.get("gateway"):
        return "gateway"
    return vendor(n.get("mac"))[1]


def _real_name(name: str | None) -> str | None:
    """systemd-resolved answers '_gateway' for the default gateway: that is not the machine's name."""
    return None if not name or name.startswith("_") else name


def _ipkey(item: dict):
    return (ORDER.get(item["kind"], 2), ipaddress.ip_address(item["ip"]))


def _items(segments, neighbors, hosts):
    """Every machine once: connected hosts (from AIOps) and neighbours (heard on the wire)."""
    by_ip = {}
    for h in hosts:
        for ip in h.get("ip_addresses") or []:
            seg = segment_of(ip, segments)
            if seg:
                by_ip[ip] = {"ip": ip, "cidr": seg["cidr"], "mac": None, "name": h["name"], "vendor": None,
                             "kind": "connected", "aiops_host": h["name"], "owner": h.get("owner"),
                             "services": list(h.get("services") or []), "talks_with": [], "last_seen": None}
    for n in neighbors:
        if n["ip"] in by_ip:
            by_ip[n["ip"]].update(mac=n.get("mac"), vendor=vendor(n.get("mac"))[0])
            continue
        seg = segment_of(n["ip"], segments)
        by_ip[n["ip"]] = {"ip": n["ip"], "cidr": n.get("cidr") or (seg or {}).get("cidr"), "mac": n.get("mac"),
                          "name": _real_name(n.get("name")), "vendor": vendor(n.get("mac"))[0], "kind": kind_of(n, seg),
                          "aiops_host": None, "owner": None, "services": [], "talks_with": list(n.get("talks_with") or []),
                          "last_seen": n.get("last_seen")}
    return sorted(by_ip.values(), key=_ipkey)


def _counts(items):
    out: dict[str, int] = {}
    for i in items:
        out[i["kind"]] = out.get(i["kind"], 0) + 1
    return out


def views(view: str, segments: list[dict], neighbors: list[dict], hosts: list[dict]) -> list[dict]:
    items = _items(segments, neighbors, hosts)
    groups: list[dict] = []
    if view == "org":
        owners = sorted({i["owner"] or "unassigned" for i in items if i["aiops_host"]})
        for o in owners:
            groups.append({"title": o, "items": [i for i in items if i["aiops_host"] and (i["owner"] or "unassigned") == o]})
        rest = [i for i in items if not i["aiops_host"]]
        if rest:
            groups.append({"title": UNKNOWN, "items": rest})
    elif view == "service":
        names = sorted({s for i in items for s in i["services"]} | {s for i in items for s in i["talks_with"]})
        used = set()
        for s in names:
            members = [i for i in items if s in i["services"]] + [i for i in items if s in i["talks_with"] and s not in i["services"]]
            used |= {i["ip"] for i in members}
            groups.append({"title": s, "items": members})
        rest = [i for i in items if i["ip"] not in used]
        if rest:
            groups.append({"title": NO_SERVICE, "items": rest})
    else:
        for seg in segments:
            members = [i for i in items if i["cidr"] == seg["cidr"]]
            seen_by = sorted({s["host"] for s in segments if s["cidr"] == seg["cidr"]})
            if not any(g["title"] == seg["cidr"] for g in groups):
                groups.append({"title": seg["cidr"], "gateway": seg.get("gateway"), "seen_by": seen_by, "items": members})
    for g in groups:
        g["counts"] = _counts(g["items"])
    return groups


# ---------------- storage (called from inventory.ingest) ----------------
FRESH = "now() - interval '1 day'"


def ingest(host: str, inv: dict):
    from . import db
    segs = []
    for i in inv.get("interfaces") or []:
        if not i.get("cidr"):
            continue
        cidr = str(ipaddress.ip_network(i["cidr"], strict=False))
        segs.append({"cidr": cidr, "gateway": i.get("gateway")})
        db.ex("""INSERT INTO net_segments(cidr, host_name, iface, gateway) VALUES (%s,%s,%s,%s)
                 ON CONFLICT (cidr, host_name) DO UPDATE SET iface=EXCLUDED.iface, gateway=EXCLUDED.gateway, last_seen=now()""",
              (cidr, host, i.get("name") or "", i.get("gateway")))
    talks: dict[str, set] = {}
    for c in inv.get("connections") or []:
        if c.get("remote_ip") and c.get("process"):
            talks.setdefault(c["remote_ip"], set()).add(c["process"])
    for n in inv.get("neighbors") or []:
        seg = segment_of(n.get("ip", ""), segs)
        if not seg:
            continue
        db.ex("""INSERT INTO net_neighbors(cidr, ip, mac, name, seen_by, talks_with, last_seen)
                 VALUES (%s,%s,%s,%s,%s,%s,COALESCE(%s, now()))
                 ON CONFLICT (cidr, ip) DO UPDATE SET mac=COALESCE(EXCLUDED.mac, net_neighbors.mac),
                   name=COALESCE(EXCLUDED.name, net_neighbors.name), seen_by=EXCLUDED.seen_by,
                   talks_with=EXCLUDED.talks_with, last_seen=GREATEST(EXCLUDED.last_seen, net_neighbors.last_seen)""",
              (seg["cidr"], n["ip"], n.get("mac"), n.get("name"), host, sorted(talks.get(n["ip"], set())),
               db.T(n.get("last_seen"))))


def load() -> tuple[list[dict], list[dict], list[dict]]:
    """Segments and neighbours heard in the last day, and the connected hosts with their services."""
    from . import db, repo
    segments = [{"cidr": r["cidr"], "gateway": r["gateway"], "host": r["host_name"], "iface": r["iface"]}
                for r in db.q(f"""SELECT s.* FROM net_segments s JOIN hosts h ON h.name = s.host_name
                                  WHERE s.last_seen > {FRESH} ORDER BY s.cidr, s.host_name""")]
    neighbors = db.q(f"SELECT * FROM net_neighbors WHERE last_seen > {FRESH}")
    svc = {}
    for r in db.q("""SELECT DISTINCT h.name AS host, s.service_name FROM service_instances i
                     JOIN services s ON s.id=i.service_id JOIN hosts h ON h.id=i.host_id"""):
        svc.setdefault(r["host"], []).append(r["service_name"])
    hosts = [{**h, "services": sorted(svc.get(h["name"], []))} for h in repo.list_hosts()]
    return segments, neighbors, hosts
