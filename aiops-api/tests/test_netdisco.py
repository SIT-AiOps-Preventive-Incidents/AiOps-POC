"""Network discovery: SNMP parsing and the layered topology, on walks shaped like net-snmp output from the lab."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.netdisco import snmp, topology  # noqa: E402

# snmpbulkwalk -v2c -c public -On -Oe -Ot <switch> <tables>   (an access switch: mgmt eth0, uplink eth1, hosts on eth2)
SW_APP = """.1.3.6.1.2.1.1.1.0 = STRING: Linux sw-app 6.8.0 #1 SMP x86_64
.1.3.6.1.2.1.1.3.0 = Timeticks: 123400
.1.3.6.1.2.1.1.5.0 = STRING: sw-app
.1.3.6.1.2.1.2.2.1.2.1 = STRING: lo
.1.3.6.1.2.1.2.2.1.2.20 = STRING: eth0
.1.3.6.1.2.1.2.2.1.2.22 = STRING: eth1
.1.3.6.1.2.1.2.2.1.2.24 = STRING: eth2
.1.3.6.1.2.1.2.2.1.5.22 = Gauge32: 10000000000
.1.3.6.1.2.1.2.2.1.6.20 = STRING: 2:42:ac:12:0:9
.1.3.6.1.2.1.2.2.1.6.22 = Hex-STRING: 02 42 0A 14 FF 03
.1.3.6.1.2.1.2.2.1.6.24 = STRING: 2:42:a:14:1:1
.1.3.6.1.2.1.2.2.1.7.22 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.8.1 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.8.20 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.8.22 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.8.24 = INTEGER: 1
.1.3.6.1.2.1.4.20.1.2.10.20.1.1 = INTEGER: 24
.1.3.6.1.2.1.4.20.1.2.10.20.255.3 = INTEGER: 22
.1.3.6.1.2.1.4.20.1.2.127.0.0.1 = INTEGER: 1
.1.3.6.1.2.1.4.20.1.2.172.18.0.9 = INTEGER: 20
.1.3.6.1.2.1.4.20.1.3.10.20.1.1 = IpAddress: 255.255.255.0
.1.3.6.1.2.1.4.20.1.3.10.20.255.3 = IpAddress: 255.255.255.248
.1.3.6.1.2.1.4.20.1.3.127.0.0.1 = IpAddress: 255.0.0.0
.1.3.6.1.2.1.4.20.1.3.172.18.0.9 = IpAddress: 255.255.0.0
.1.3.6.1.2.1.4.22.1.2.20.172.18.0.1 = STRING: 2:42:7c:1:2:3
.1.3.6.1.2.1.4.22.1.2.22.10.20.255.2 = STRING: 2:42:a:14:ff:2
.1.3.6.1.2.1.4.22.1.2.24.10.20.1.11 = STRING: 2:42:a:14:1:b
.1.3.6.1.2.1.4.22.1.2.24.10.20.1.13 = STRING: 2:42:a:14:1:d
.1.3.6.1.2.1.4.22.1.2.24.10.20.1.99 = STRING: 2:42:a:14:1:63
.1.3.6.1.2.1.4.22.1.4.24.10.20.1.11 = INTEGER: 3
.1.3.6.1.2.1.4.22.1.4.24.10.20.1.13 = INTEGER: 3
.1.3.6.1.2.1.4.22.1.4.24.10.20.1.99 = INTEGER: 3
.1.0.8802.1.1.2.1.3.7.1.3.22 = STRING: eth1
.1.0.8802.1.1.2.1.3.7.1.4.22 = STRING: eth1
.1.0.8802.1.1.2.1.4.1.1.7.0.22.1 = Hex-STRING: 02 42 0A 14 FF 02
.1.0.8802.1.1.2.1.4.1.1.8.0.22.1 = STRING: eth1
.1.0.8802.1.1.2.1.4.1.1.9.0.22.1 = STRING: core-rtr
"""

CORE = """.1.3.6.1.2.1.1.5.0 = STRING: core-rtr
.1.3.6.1.2.1.2.2.1.2.10 = STRING: eth0
.1.3.6.1.2.1.2.2.1.2.11 = STRING: eth1
.1.3.6.1.2.1.2.2.1.2.12 = STRING: eth2
.1.3.6.1.2.1.2.2.1.6.11 = STRING: 2:42:a:14:ff:2
.1.3.6.1.2.1.2.2.1.8.10 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.8.11 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.8.12 = INTEGER: 1
.1.3.6.1.2.1.4.20.1.2.172.18.0.8 = INTEGER: 10
.1.3.6.1.2.1.4.20.1.2.10.20.255.2 = INTEGER: 11
.1.3.6.1.2.1.4.20.1.2.10.20.255.10 = INTEGER: 12
.1.3.6.1.2.1.4.20.1.3.172.18.0.8 = IpAddress: 255.255.0.0
.1.3.6.1.2.1.4.20.1.3.10.20.255.2 = IpAddress: 255.255.255.248
.1.3.6.1.2.1.4.20.1.3.10.20.255.10 = IpAddress: 255.255.255.248
.1.3.6.1.2.1.4.22.1.2.11.10.20.255.3 = STRING: 2:42:a:14:ff:3
.1.3.6.1.2.1.4.22.1.4.11.10.20.255.3 = INTEGER: 3
.1.0.8802.1.1.2.1.4.1.1.7.0.11.1 = STRING: eth1
.1.0.8802.1.1.2.1.4.1.1.8.0.11.1 = STRING: eth1
.1.0.8802.1.1.2.1.4.1.1.9.0.11.1 = STRING: sw-app
"""

ENDPOINTS = {"10.20.1.11": {"name": "frontend-a", "kind": "container", "services": ["frontend"]},
             "10.20.1.13": {"name": "checkout", "kind": "container", "services": ["checkout"]}}


def devices(sw=SW_APP, core=CORE):
    return [snmp.parse_device("172.18.0.9", snmp.parse_walk(sw)), snmp.parse_device("172.18.0.8", snmp.parse_walk(core))]


def node(topo, nid):
    return next(n for n in topo["nodes"] if n["id"] == nid)


# ---------------- snmp parsing ----------------
def test_parse_walk_types_quotes_and_wrapped_hex():
    rows = snmp.parse_walk('.1.3.6.1.2.1.1.5.0 = STRING: "sw-app"\n'
                           '.1.3.6.1.2.1.1.6.0 = Hex-STRING: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F\n'
                           '10 11\n'
                           '.1.3.6.1.2.1.1.7.0 = No Such Object available on this agent at this OID\n')
    assert rows[".1.3.6.1.2.1.1.5.0"] == "sw-app"
    assert rows[".1.3.6.1.2.1.1.6.0"].endswith("0f:10:11")
    assert ".1.3.6.1.2.1.1.7.0" not in rows


def test_mac_normalisation():
    assert snmp.mac("2:42:a:14:1:b") == "02:42:0a:14:01:0b"
    assert snmp.mac("02 42 0A 14 FF 03") == "02:42:0a:14:ff:03"
    assert snmp.mac("") == "" and snmp.mac("eth1") == ""


def test_parse_device_ports_ips_arp_lldp():
    d = devices()[0]
    assert d.name == "sw-app" and d.uptime_s == 1234 and d.descr.startswith("Linux")
    assert {p.name for p in d.ports.values()} == {"lo", "eth0", "eth1", "eth2"}
    assert d.port_by_name("eth1").mac == "02:42:0a:14:ff:03" and d.port_by_name("eth1").speed_mbps == 10000
    assert [str(i) for i in d.port_by_name("eth2").ips] == ["10.20.1.1/24"]
    assert d.mgmt_port == "eth0"
    assert ("eth2", "10.20.1.13", "02:42:0a:14:01:0d") in [(a.port, a.ip, a.mac) for a in d.arp]
    assert [(n.port, n.system, n.remote_port) for n in d.neighbors] == [("eth1", "core-rtr", "02:42:0a:14:ff:02")]


# ---------------- topology ----------------
def test_layers_from_core_to_services():
    t = topology.build(devices(), ENDPOINTS, now=1000)
    assert node(t, "dev:core-rtr")["role"] == "core" and node(t, "dev:sw-app")["role"] == "access"
    assert node(t, "host:02:42:0a:14:01:0d")["name"] == "checkout"
    assert node(t, "svc:checkout")["layer"] == 3 and node(t, "svc:frontend")["reachable"]
    cable = next(l for l in t["links"] if l["kind"] == "cable")
    assert {cable["a"], cable["b"]} == {"dev:core-rtr", "dev:sw-app"} and cable["status"] == "up"
    assert {cable["a_port"], cable["b_port"]} == {"eth1"}   # LLDP port id was a MAC, resolved to the port name


def test_management_and_device_addresses_are_not_hosts():
    hosts = [n for n in topology.build(devices(), ENDPOINTS, now=1)["nodes"] if n["kind"] == "host"]
    assert sorted(h["ip"] for h in hosts) == ["10.20.1.11", "10.20.1.13", "10.20.1.99"]


def test_unknown_address_is_an_unknown_host():
    h = node(topology.build(devices(), ENDPOINTS, now=1), "host:02:42:0a:14:01:63")
    assert h["known"] is False and h["name"] == "unknown 10.20.1.99"


def test_first_scan_has_no_events_second_reports_changes():
    first = topology.build(devices(), ENDPOINTS, now=1000)
    assert first["events"] == []
    known = {"assets": {n["id"]: n for n in first["nodes"]}, "links": {l["id"]: l for l in first["links"]}}
    rogue = SW_APP + (".1.3.6.1.2.1.4.22.1.2.24.10.20.1.66 = STRING: 2:42:a:14:1:42\n"
                      ".1.3.6.1.2.1.4.22.1.4.24.10.20.1.66 = INTEGER: 3\n")
    second = topology.build(devices(sw=rogue), ENDPOINTS, known, now=1060)
    assert [(e["kind"], e["entity"]) for e in second["events"]] == [("host_unknown", "host:02:42:0a:14:01:42")]
    assert node(second, "host:02:42:0a:14:01:42")["new"] is True
    assert node(second, "host:02:42:0a:14:01:0d")["new"] is False


def test_uplink_down_cuts_off_hosts_and_services_and_is_an_event():
    first = topology.build(devices(), ENDPOINTS, now=1000)
    known = {"assets": {n["id"]: n for n in first["nodes"]}, "links": {l["id"]: l for l in first["links"]}}
    # sw-app eth1 goes down; its LLDP entry ages out
    down = SW_APP.replace(".1.3.6.1.2.1.2.2.1.8.22 = INTEGER: 1", ".1.3.6.1.2.1.2.2.1.8.22 = INTEGER: 2")
    down = "\n".join(l for l in down.splitlines() if ".1.0.8802.1.1.2.1.4.1.1" not in l)
    core = "\n".join(l for l in CORE.splitlines() if ".1.0.8802.1.1.2.1.4.1.1" not in l)
    t = topology.build(devices(sw=down, core=core), ENDPOINTS, known, now=1060)
    cable = next(l for l in t["links"] if l["kind"] == "cable")
    assert cable["status"] == "down"
    assert node(t, "host:02:42:0a:14:01:0d")["status"] == "cut off"
    assert topology.impacted_services(t) == ["checkout", "frontend"]
    kinds = [e["kind"] for e in t["events"]]
    assert kinds.count("link_down") == 1 and kinds.count("host_cut_off") == 3


def test_host_port_down_marks_host_down():
    first = topology.build(devices(), ENDPOINTS, now=1000)
    down = SW_APP.replace(".1.3.6.1.2.1.2.2.1.8.24 = INTEGER: 1", ".1.3.6.1.2.1.2.2.1.8.24 = INTEGER: 2")
    t = topology.build(devices(sw=down), ENDPOINTS, {"assets": {n["id"]: n for n in first["nodes"]},
                                                     "links": {l["id"]: l for l in first["links"]}}, now=1060)
    assert node(t, "host:02:42:0a:14:01:0d")["status"] == "down"
    assert "checkout" in topology.impacted_services(t)


def test_device_unreachable_and_host_missing():
    first = topology.build(devices(), ENDPOINTS, now=1000)
    known = {"assets": {n["id"]: n for n in first["nodes"]}, "links": {l["id"]: l for l in first["links"]}}
    gone = snmp.Device(address="172.18.0.9", name="sw-app", reachable=False, error="Timeout")
    t = topology.build([gone, devices()[1]], ENDPOINTS, known, now=1060)
    assert node(t, "dev:sw-app")["status"] == "unreachable"
    assert node(t, "host:02:42:0a:14:01:0d")["status"] == "missing"
    kinds = {e["kind"] for e in t["events"]}
    assert {"device_down", "link_down", "host_missing"} <= kinds
    later = topology.build([gone, devices()[1]], ENDPOINTS, known, now=1000 + topology.MISSING_KEEP_S + 1)
    assert not any(n["id"] == "host:02:42:0a:14:01:0d" for n in later["nodes"])


def test_poll_resolves_names_and_reports_unreachable(monkeypatch):
    import asyncio

    async def no_answer(ip, community="public", timeout_s=2):
        assert ip == "127.0.0.1"          # polled by address, so the management port is recognised
        raise ConnectionError("Timeout: No Response from 127.0.0.1")
    monkeypatch.setattr(snmp, "walk", no_answer)
    d = asyncio.run(snmp.poll("localhost"))
    assert d.reachable is False and d.address == "127.0.0.1" and d.name == "localhost" and "Timeout" in d.error
    bad = asyncio.run(snmp.poll("no-such-device.invalid"))
    assert bad.reachable is False and bad.error.startswith("cannot resolve")


def test_scenario_port_command_targets_the_right_port():
    from app.netdisco import scenarios
    cmd = scenarios._port_cmd("10.20.255.", "down")[2]
    assert "/^10\\.20\\.255\\./" in cmd and cmd.endswith(" down")


def test_own_lldp_frames_heard_back_are_not_neighbours():
    echo = SW_APP + (".1.0.8802.1.1.2.1.4.1.1.9.0.24.2 = STRING: sw-app\n"
                     ".1.0.8802.1.1.2.1.4.1.1.7.0.24.2 = STRING: eth2\n")
    d = snmp.parse_device("172.18.0.9", snmp.parse_walk(echo))
    assert [n.system for n in d.neighbors] == ["core-rtr"]


def test_stored_self_link_is_ignored():
    first = topology.build(devices(), ENDPOINTS, now=1000)
    known = {"assets": {n["id"]: n for n in first["nodes"]}, "links": {l["id"]: l for l in first["links"]}}
    known["links"]["sw-app:eth1--sw-app:eth1"] = {"id": "sw-app:eth1--sw-app:eth1", "kind": "cable", "a": "dev:sw-app",
                                                  "a_port": "eth1", "b": "dev:sw-app", "b_port": "eth1", "status": "up"}
    t = topology.build(devices(), ENDPOINTS, known, now=1060)
    assert not any(l["a"] == l["b"] for l in t["links"])


def test_tunnels_and_loopback_are_not_ports():
    tun = SW_APP + (".1.3.6.1.2.1.2.2.1.2.30 = STRING: tunl0\n.1.3.6.1.2.1.2.2.1.3.30 = INTEGER: 131\n"
                    ".1.3.6.1.2.1.2.2.1.8.30 = INTEGER: 2\n.1.3.6.1.2.1.2.2.1.3.1 = INTEGER: 24\n"
                    ".1.3.6.1.2.1.2.2.1.2.31 = STRING: gretap0\n.1.3.6.1.2.1.2.2.1.3.31 = INTEGER: 6\n")
    d = snmp.parse_device("172.18.0.9", snmp.parse_walk(tun))
    ports = node(topology.build([d], ENDPOINTS, now=1), "dev:sw-app")["ports"]
    assert [p["name"] for p in ports] == ["eth0", "eth1", "eth2"]
