"""Your network: what a connected server hears on its own network segment, grouped by network, service or owner."""
from __future__ import annotations

import importlib.util
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import netseg  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "netwatch", os.path.join(os.path.dirname(__file__), "..", "app", "agent_dist", "netwatch.py"))
netwatch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(netwatch)


def arp_frame(sender_mac: str, sender_ip: str, op: int = 1, vlan: int | None = None) -> bytes:
    mac = bytes.fromhex(sender_mac.replace(":", ""))
    eth = b"\xff" * 6 + mac + (struct.pack("!HH", 0x8100, vlan) if vlan else b"") + struct.pack("!H", 0x0806)
    arp = struct.pack("!HHBBH", 1, 0x0800, 6, 4, op) + mac + bytes(map(int, sender_ip.split("."))) + b"\x00" * 6 \
        + bytes([10, 4, 82, 254])
    return eth + arp


def test_active_sweep_asks_only_who_has_on_our_own_segment():
    import socket
    own_ip = struct.unpack("!I", socket.inet_aton("10.4.82.20"))[0]
    target = struct.unpack("!I", socket.inet_aton("10.4.82.31"))[0]
    f = netwatch._arp_request(own_ip, bytes.fromhex("001122334455"), target)
    assert f[:6] == b"\xff" * 6                                   # broadcast on the local segment, not a routed packet
    assert f[12:14] == b"\x08\x06"                                # ARP, never a TCP/UDP service probe
    htype, ptype, hlen, plen, op = struct.unpack("!HHBBH", f[14:24])
    assert op == 1 and ptype == 0x0800                           # "who has", a request, not a reply or anything else
    assert f[14 + 8 + 6 + 6:14 + 8 + 6 + 6 + 4] == socket.inet_aton("10.4.82.31")
    assert netwatch.SWEEP_MAX <= 1024 and netwatch.SWEEP_RATE <= 100   # bounded: at most a /22, rate-limited


def test_arp_gives_who_is_where_and_nothing_else():
    assert netwatch.parse_arp(arp_frame("bc:24:11:12:34:56", "10.4.82.31")) == ("10.4.82.31", "bc:24:11:12:34:56")
    assert netwatch.parse_arp(arp_frame("bc:24:11:12:34:56", "10.4.82.31", op=2, vlan=82)) == ("10.4.82.31", "bc:24:11:12:34:56")
    assert netwatch.parse_arp(arp_frame("bc:24:11:12:34:56", "0.0.0.0")) is None          # address probe, no owner yet
    assert netwatch.parse_arp(b"\x00" * 20) is None
    assert netwatch.parse_arp(b"\xff" * 12 + b"\x08\x00" + b"\x00" * 28) is None         # IPv4, not ARP


def test_watcher_ignores_container_and_loopback_interfaces():
    assert netwatch.watched("eth0") and netwatch.watched("ens18") and netwatch.watched("enp1s0")
    for name in ("lo", "docker0", "br-7af78d5ecf88", "veth130ef83", "virbr0", "cni0", "tailscale0"):
        assert not netwatch.watched(name), name


def test_the_mac_says_what_kind_of_machine_it_is():
    assert netseg.vendor("BC:24:11:aa:bb:cc") == ("Proxmox", "virtual machine")
    assert netseg.vendor("52:54:00:aa:bb:cc") == ("QEMU/KVM", "virtual machine")
    assert netseg.vendor("00:50:56:aa:bb:cc") == ("VMware", "virtual machine")
    assert netseg.vendor("00:15:5d:aa:bb:cc") == ("Hyper-V", "virtual machine")
    assert netseg.vendor("02:42:ac:11:00:02") == ("Docker", "container")
    assert netseg.vendor("c4:12:ec:d1:e6:9e") == (None, "device")
    assert netseg.vendor("06:aa:bb:cc:dd:ee") == (None, "random MAC")


def test_the_gateway_is_named_as_such():
    seg = {"cidr": "10.4.82.0/24", "gateway": "10.4.82.254"}
    assert netseg.kind_of({"ip": "10.4.82.254", "mac": "c4:12:ec:d1:e6:9e"}, seg) == "gateway"
    assert netseg.kind_of({"ip": "10.4.82.31", "mac": "bc:24:11:00:00:01"}, seg) == "virtual machine"
    assert netseg.segment_of("10.4.82.31", [seg]) == seg and netseg.segment_of("8.8.8.8", [seg]) is None


SEGS = [{"cidr": "10.4.82.0/24", "gateway": "10.4.82.254", "host": "cp26pt1", "iface": "eth0"}]
NEIGH = [
    {"cidr": "10.4.82.0/24", "ip": "10.4.82.254", "mac": "c4:12:ec:d1:e6:9e", "name": None, "talks_with": [], "last_seen": 100},
    {"cidr": "10.4.82.0/24", "ip": "10.4.82.31", "mac": "bc:24:11:00:00:01", "name": "cp26pt2.sit.kmutt.ac.th",
     "talks_with": [], "last_seen": 90},
    {"cidr": "10.4.82.0/24", "ip": "10.4.82.12", "mac": "bc:24:11:00:00:02", "name": None, "talks_with": ["postgres"],
     "last_seen": 80},
]
HOSTS = [{"name": "cp26pt1", "ip_addresses": ["10.4.82.20"], "owner": "team-platform", "services": ["aiops-api", "postgres"]}]


def test_network_view_is_one_group_per_segment_gateway_first():
    g = netseg.views("network", SEGS, NEIGH, HOSTS)
    assert [x["title"] for x in g] == ["10.4.82.0/24"]
    items = g[0]["items"]
    assert [i["ip"] for i in items] == ["10.4.82.254", "10.4.82.20", "10.4.82.12", "10.4.82.31"]
    assert items[0]["kind"] == "gateway" and items[1]["aiops_host"] == "cp26pt1"
    assert items[3]["name"] == "cp26pt2.sit.kmutt.ac.th" and items[3]["vendor"] == "Proxmox"
    assert g[0]["counts"] == {"gateway": 1, "virtual machine": 2, "connected": 1}


def test_org_view_groups_by_owner_and_keeps_the_unknown_apart():
    g = netseg.views("org", SEGS, NEIGH, HOSTS)
    assert [x["title"] for x in g] == ["team-platform", "Not connected to AIOps"]
    assert [i["ip"] for i in g[0]["items"]] == ["10.4.82.20"]
    assert len(g[1]["items"]) == 3


def test_service_view_puts_machines_under_the_services_that_use_them():
    g = {x["title"]: [i["ip"] for i in x["items"]] for x in netseg.views("service", SEGS, NEIGH, HOSTS)}
    assert g["aiops-api"] == ["10.4.82.20"]
    assert g["postgres"] == ["10.4.82.20", "10.4.82.12"]                  # runs here, and talks to .12
    assert g["No known service"] == ["10.4.82.254", "10.4.82.31"]


def test_graph_is_internet_gateway_hub_machines_services():
    hosts = HOSTS + [{"name": "esg360-prod", "ip_addresses": ["10.148.0.4", "172.17.0.1"], "owner": "team-esg",
                      "services": ["one-esg-360"], "status": "healthy"}]
    g = netseg.graph(SEGS, NEIGH, hosts, {"postgres": "problem", "aiops-api": "healthy"},
                     [{"from": "aiops-api", "to": "postgres"}])
    ids = [n["id"] for n in g["nodes"]]
    assert len(ids) == len(set(ids))                                           # every object once
    kinds = {n["id"]: n["kind"] for n in g["nodes"]}
    assert kinds["internet"] == "internet" and kinds["hub:10.4.82.0/24"] == "hub"
    assert kinds["gw:10.4.82.254"] == "gateway" and kinds["host:cp26pt1"] == "connected"
    assert kinds["ip:10.4.82.31"] == "virtual machine" and kinds["svc:postgres"] == "service"
    links = {(l["source"], l["target"]) for l in g["links"]}
    assert ("gw:10.4.82.254", "internet") in links and ("hub:10.4.82.0/24", "gw:10.4.82.254") in links
    assert ("host:cp26pt1", "hub:10.4.82.0/24") in links and ("ip:10.4.82.31", "hub:10.4.82.0/24") in links
    assert ("svc:postgres", "host:cp26pt1") in links
    assert ("svc:aiops-api", "svc:postgres") in links                         # who talks to whom
    est = next(n for n in g["nodes"] if n["id"] == "hub:10.148.0.0/24")       # no segment reported: from its IP
    assert est["estimated"] is True and ("hub:10.148.0.0/24", "internet") in links
    assert ("host:esg360-prod", "hub:10.148.0.0/24") in links
    assert not any(n["id"].startswith("hub:172.17") for n in g["nodes"])      # Docker bridges are not networks
    assert next(n for n in g["nodes"] if n["id"] == "svc:postgres")["status"] == "problem"
