"""NIKA (Kathara) labs as a discovery source, on output captured from a real dc_clos lab."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.netdisco import kathara, topology  # noqa: E402

LINK = ("{n}: {eth}: <BROADCAST,MULTICAST,{flags}> mtu 1500 qdisc fq_codel state {state} mode DEFAULT group default "
        "qlen 1000\\    link/ether {mac} brd ff:ff:ff:ff:ff:ff\\    alias nika:tap:b96344781db\n")


def probe(ports, svc=(), bgp=None):
    addr = "1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever preferred_lft forever\n"
    link = ("1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000"
            "\\    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00\n")
    for i, (eth, ip, mac, up) in enumerate(ports, start=120):
        addr += f"{i}: {eth}    inet {ip} scope global {eth}\\       valid_lft forever preferred_lft forever\n"
        link += LINK.format(n=i, eth=eth, mac=mac, flags="UP,LOWER_UP" if up else "", state="UP" if up else "DOWN")
    text = addr + "##\n" + link + "##\n" + "".join(f"svc={s}\n" for s in svc) + "##\n"
    if bgp is not None:
        text += bgp if isinstance(bgp, str) else json.dumps({"ipv4Unicast": {"peers": bgp}})
    return text


def peers(*names, state="Established"):
    return {f"172.16.0.{i}": {"hostname": n, "state": state} for i, n in enumerate(names)}


def lab(spine_bgp_state="Established", dns_up=True, leaf_eth0_up=True):
    """spine_0 -- leaf_0 -- dns_pod0 ; spine_0 -- super_spine -- client_0"""
    return [
        {"name": "spine_router_0_0", "image": "nika/frr:0.2.0", "links": {"eth0": "l_spine_leaf", "eth1": "l_ss_spine"},
         "probe": kathara.parse_probe(probe([("eth0", "172.16.0.4/31", "1e:5f:16:49:7e:24", True),
                                            ("eth1", "172.16.0.1/31", "1e:5f:16:49:7e:25", True)],
                                           bgp=peers("leaf_router_0_0", state=spine_bgp_state)))},
        {"name": "leaf_router_0_0", "image": "nika/frr:0.2.0", "links": {"eth0": "l_spine_leaf", "eth2": "l_leaf_dns"},
         "probe": kathara.parse_probe(probe([("eth0", "172.16.0.5/31", "a6:ae:50:b9:14:12", leaf_eth0_up),
                                            ("eth2", "10.0.0.1/24", "ce:71:90:03:eb:3e", True)], bgp=peers("spine_router_0_0")))},
        {"name": "super_spine_router_0", "image": "nika/frr:0.2.0", "links": {"eth0": "l_ss_spine", "eth2": "l_ss_client"},
         "probe": kathara.parse_probe(probe([("eth0", "172.16.0.0/31", "aa:00:00:00:00:01", True),
                                            ("eth2", "192.168.0.1/24", "aa:00:00:00:00:02", True)], bgp=peers("spine_router_0_0")))},
        {"name": "dns_pod0", "image": "nika/base:0.2.0", "links": {"eth0": "l_leaf_dns"},
         "probe": kathara.parse_probe(probe([("eth0", "10.0.0.2/24", "ae:12:7a:fa:f0:96", dns_up)], svc=("dns",)))},
        {"name": "client_0", "image": "nika/base:0.2.0", "links": {"eth0": "l_ss_client"},
         "probe": kathara.parse_probe(probe([("eth0", "192.168.0.2/24", "bb:00:00:00:00:01", True)]))},
    ]


def topo(nodes, known=None, now=1000):
    devices, endpoints = kathara.build(nodes)
    return topology.build(devices, endpoints, known, now=now)


def node(t, nid):
    return next(n for n in t["nodes"] if n["id"] == nid)


def test_parse_probe_real_output():
    p = kathara.parse_probe(probe([("eth0", "172.16.0.5/31", "a6:ae:50:b9:14:12", True)], bgp=peers("spine_router_0_0")))
    assert p["router"] and p["bgp"]["ok"] and p["ports"]["eth0"] == {"up": True, "mac": "a6:ae:50:b9:14:12", "ips": ["172.16.0.5/31"]}
    host = kathara.parse_probe(probe([("eth0", "10.0.0.2/24", "ae:12:7a:fa:f0:96", True)], svc=("dns",)))
    assert not host["router"] and host["services"] == ["dns"]
    assert kathara.parse_probe(probe([], bgp="BGP_DOWN"))["bgp"]["ok"] is False


def test_research_topology_becomes_the_map():
    t = topo(lab())
    cables = sorted(l["id"] for l in t["links"] if l["kind"] == "cable")
    assert cables == ["leaf_router_0_0:eth0--spine_router_0_0:eth0", "spine_router_0_0:eth1--super_spine_router_0:eth0"]
    assert node(t, "dev:spine_router_0_0")["role"] == "core" and node(t, "dev:leaf_router_0_0")["role"] == "access"
    assert node(t, "host:dns_pod0")["name"] == "dns_pod0" and node(t, "svc:dns")["reachable"]
    assert node(t, "dev:leaf_router_0_0")["ip"] == ""          # no management address on a lab node


def test_link_down_on_the_host_side_marks_host_and_service():
    first = topo(lab())
    known = {"assets": {n["id"]: n for n in first["nodes"]}, "links": {l["id"]: l for l in first["links"]}}
    t = topo(lab(dns_up=False), known, now=1060)
    assert node(t, "host:dns_pod0")["status"] == "down"
    assert topology.impacted_services(t) == ["dns"]


def test_fabric_link_down_cuts_off_what_is_behind_it():
    first = topo(lab())
    known = {"assets": {n["id"]: n for n in first["nodes"]}, "links": {l["id"]: l for l in first["links"]}}
    t = topo(lab(leaf_eth0_up=False), known, now=1060)
    cable = next(l for l in t["links"] if l["id"] == "leaf_router_0_0:eth0--spine_router_0_0:eth0")
    assert cable["status"] == "down" and node(t, "host:dns_pod0")["status"] == "cut off"
    assert "link_down" in [e["kind"] for e in t["events"]]


def test_router_without_bgp_does_not_route():
    first = topo(lab())
    known = {"assets": {n["id"]: n for n in first["nodes"]}, "links": {l["id"]: l for l in first["links"]}}
    t = topo(lab(spine_bgp_state="Active"), known, now=1060)
    assert node(t, "dev:spine_router_0_0")["status"] == "routing down"
    assert "routing_down" in [e["kind"] for e in t["events"]]
    assert node(t, "host:dns_pod0")["status"] == "cut off"    # the only path ran through the spine


def test_redeployed_lab_keeps_its_hosts():
    first = topo(lab())
    known = {"assets": {n["id"]: n for n in first["nodes"]}, "links": {l["id"]: l for l in first["links"]}}
    again = lab()
    again[3]["probe"]["ports"]["eth0"]["mac"] = "02:00:00:00:00:99"     # same node, new MAC after a redeploy
    t = topo(again, known, now=1060)
    assert t["events"] == [] and node(t, "host:dns_pod0")["mac"] == "02:00:00:00:00:99"
