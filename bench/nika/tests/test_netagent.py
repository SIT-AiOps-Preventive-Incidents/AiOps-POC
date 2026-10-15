"""Evidence parsers and rules, on command output shaped like a real dc_clos lab. No NIKA, no lab, no LLM."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from netagent import evidence, skills  # noqa: E402

CLIENT_OK = """##addr
lo               UNKNOWN        127.0.0.1/8
eth0@if12        UP             192.168.0.2/24
##link
lo               UNKNOWN        00:00:00:00:00:00
eth0@if12        UP             aa:bb:cc:00:00:01
##route
default via 192.168.0.1 dev eth0
192.168.0.0/24 dev eth0 proto kernel scope link src 192.168.0.2
##gwping
192.168.0.1 ok
##resolv
nameserver 10.0.0.2
##qdisc
##fw
##cpu
4
0.80
 0.3 bash
 0.0 ps
##dns
##bgp
"""

DNS_OK = """##addr
eth0@if20        UP             10.0.0.2/24
##link
eth0@if20        UP             aa:bb:cc:00:00:02
##route
default via 10.0.0.1 dev eth0
10.0.0.0/24 dev eth0 proto kernel scope link src 10.0.0.2
##gwping
10.0.0.1 ok
##resolv
nameserver 127.0.0.1
##qdisc
##fw
##cpu
4
0.80
 1.2 named
##dns
named=up
web0 IN  A  10.0.1.2
zone "pod0"
##bgp
"""

ROUTER_OK = """##addr
eth0@if3         UP             172.16.0.1/31
eth2@if9         UP             192.168.0.1/24
##link
eth0@if3         UP             aa:bb:cc:00:00:10
eth2@if9         UP             aa:bb:cc:00:00:12
##route
10.0.0.0/24 nhid 12 via 172.16.0.0 dev eth0 proto bgp metric 20
##gwping
##resolv
##qdisc
##fw
##cpu
4
0.80
 0.4 bgpd
 0.1 zebra
##dns
##bgp
Neighbor        V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd   PfxSnt Desc
172.16.0.0      4      65100        40        42        0    0    0 00:10:01            3        4 N/A
"""


def lab(**over):
    texts = {"client_0": CLIENT_OK, "dns_pod0": DNS_OK, "super_spine_router_0": ROUTER_OK}
    texts.update(over)
    return {n: evidence.parse_device(n, t) for n, t in texts.items()}


def dns_ok():
    return [evidence.parse_dns("client_0", "10.0.0.2", "web0.pod0",
                               "##direct\n;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1\n;; Query time: 3 msec\n"
                               "##resolver\nrc=0 ms=5\n")]


def faults(devs, dns=None):
    return [(f.fault, f.node, f.iface) for f in skills.analyse(devs, dns if dns is not None else dns_ok(), {"client_0"})]


CONTEXT = {
    "fault_ontology": [{"id": i, "owner_kind": k} for i, k in [
        ("host_incorrect_dns", "node"), ("host_incorrect_gateway", "node"), ("dns_service_down", "node"),
        ("dns_lookup_latency", "node"), ("receiver_resource_contention", "node"), ("link_down", "link"),
        ("icmp_acl_block", "node"), ("http_acl_block", "node"), ("host_static_blackhole", "node"),
        ("link_bandwidth_throttling", "interface")]],
    "resources": [{"id": i} for i in ["node/client_0", "node/dns_pod0", "node/super_spine_router_0",
                                       "link/client_0:eth0--super_spine_router_0:eth2", "interface/client_0/eth0"]],
}


# ---------------- parsing ----------------
def test_parse_device_reads_every_section():
    d = evidence.parse_device("client_0", CLIENT_OK)
    assert [str(a) for a in d.addrs] == ["192.168.0.2/24"]
    assert d.default_gw == "192.168.0.1" and d.gw_answers is True
    assert d.nameservers == ["10.0.0.2"] and d.nproc == 4 and not d.is_router and not d.dns_server


def test_parse_dns_server_and_router():
    d = evidence.parse_device("dns_pod0", DNS_OK)
    assert d.dns_server and d.named_up and d.dns_names == ["web0.pod0"]
    r = evidence.parse_device("super_spine_router_0", ROUTER_OK)
    assert r.is_router and r.bgp_down == []


def test_bgp_neighbor_not_established_is_seen():
    r = evidence.parse_device("super_spine_router_0", ROUTER_OK.replace(
        "00:10:01            3        4 N/A", "never          Active        0 N/A"))
    assert r.bgp_down == ["172.16.0.0 Active"]


def test_parse_dns_timeout_and_slow():
    t = evidence.parse_dns("c", "10.0.0.2", "w", "##direct\n;; connection timed out; no servers could be reached\n##resolver\nrc=2 ms=5003\n")
    assert t.direct_ok is False and t.resolver_ok is False and t.resolver_ms == 5003
    s = evidence.parse_dns("c", "10.0.0.2", "w", "##direct\n;; status: NOERROR\n;; Query time: 1004 msec\n##resolver\nrc=0 ms=1010\n")
    assert s.direct_ok and s.direct_ms == 1004


def test_probe_commands_are_read_only():
    cmd = evidence.device_probe() + evidence.dns_probe("10.0.0.2", "web0.pod0")
    for verb in ("ip link set", "ip route add", "ip route del", "iptables -A", "iptables -D", "iptables -I", "tc qdisc add",
                 "tc qdisc del", "systemctl", "kill", "rm ", "> /etc"):
        assert verb not in cmd


# ---------------- rules ----------------
def test_healthy_lab_has_no_findings():
    assert faults(lab()) == []


def test_wrong_resolver():
    assert faults(lab(client_0=CLIENT_OK.replace("nameserver 10.0.0.2", "nameserver 10.9.9.9"))) == [("host_incorrect_dns", "client_0", "")]


def test_wrong_gateway_off_subnet_and_silent():
    off = lab(client_0=CLIENT_OK.replace("default via 192.168.0.1", "default via 192.168.7.1").replace("192.168.0.1 ok", "192.168.7.1 fail"))
    assert ("host_incorrect_gateway", "client_0", "") in faults(off)
    silent = lab(client_0=CLIENT_OK.replace("default via 192.168.0.1", "default via 192.168.0.99").replace("192.168.0.1 ok", "192.168.0.99 fail"))
    assert faults(silent) == [("host_incorrect_gateway", "client_0", "")]


def test_dns_down():
    assert faults(lab(dns_pod0=DNS_OK.replace("named=up", "named=down"))) == [("dns_service_down", "dns_pod0", "")]


def test_dns_delay_qdisc_is_direct_proof():
    devs = lab(dns_pod0=DNS_OK.replace("##qdisc\n", "##qdisc\nqdisc netem 8001: dev eth0 root refcnt 2 limit 1000 delay 1s\n"))
    assert faults(devs)[0] == ("dns_lookup_latency", "dns_pod0", "")


def test_slow_dns_without_a_visible_cause_still_points_at_the_server():
    slow = [evidence.parse_dns("client_0", "10.0.0.2", "web0.pod0", "##direct\n;; status: NOERROR\n;; Query time: 1004 msec\n##resolver\nrc=0 ms=1010\n")]
    assert faults(lab(), slow) == [("dns_lookup_latency", "dns_pod0", "")]


def test_cpu_contention_summed_across_capped_workers():
    hog = CLIENT_OK.replace(" 0.3 bash", " 12.4 stress-ng-cpu\n 12.3 stress-ng-cpu\n 12.1 stress-ng-cpu\n 12.0 stress-ng-cpu")
    assert faults(lab(client_0=hog)) == [("receiver_resource_contention", "client_0", "")]


def test_busy_dns_daemon_is_not_contention():
    assert faults(lab(dns_pod0=DNS_OK.replace(" 1.2 named", " 85.0 named"))) == []


def test_link_down():
    devs = lab(client_0=CLIENT_OK.replace("eth0@if12        UP             aa", "eth0@if12        DOWN           aa"))
    assert ("link_down", "client_0", "eth0") in faults(devs)


def test_acl_rules_by_traffic_kind():
    assert skills.acl_fault("-A INPUT -p icmp -j DROP") == "icmp_acl_block"
    assert skills.acl_fault("-A INPUT -p tcp -m tcp --dport 80 -j DROP") == "http_acl_block"
    assert skills.acl_fault("ip protocol icmp drop") == "icmp_acl_block"
    assert skills.acl_fault("tcp dport 179 drop") == "bgp_acl_block"
    assert skills.acl_fault("-A INPUT -p udp --dport 53 -j REJECT") == "dns_port_blocked"
    assert skills.acl_fault("-A OUTPUT -p icmp --icmp-type fragmentation-needed -j DROP") == "icmp_frag_needed_filter_misconfiguration"
    assert skills.acl_fault(":INPUT DROP [0:0]") is None   # a policy line names no traffic
    assert skills.acl_fault("-A INPUT -p icmp -j ACCEPT") is None


def test_blackhole_route_on_router():
    devs = lab(super_spine_router_0=ROUTER_OK.replace("##gwping", "blackhole 10.0.1.0/24 proto static\n##gwping"))
    assert faults(devs) == [("host_static_blackhole", "super_spine_router_0", "")]


# ---------------- submission ----------------
def test_submission_maps_to_catalog_ids():
    f = [skills.Finding("link_down", "client_0", "eth0", "", 3)]
    assert skills.submission(f, [], CONTEXT) == {
        "is_anomaly": True, "root_causes": [{"resource_id": "link/client_0:eth0--super_spine_router_0:eth2", "fault_type": "link_down"}]}


def test_submission_healthy_and_symptom_only():
    assert skills.submission([], [], CONTEXT) == {"is_anomaly": False, "root_causes": []}
    assert skills.submission([], ["client_0 -> dns_pod0: unreachable"], CONTEXT) == {"is_anomaly": True, "root_causes": []}


def test_submission_drops_unknown_ids_and_weaker_guesses():
    f = [skills.Finding("dns_service_down", "dns_pod0", "", "", 3),
         skills.Finding("receiver_resource_contention", "client_0", "", "", 2),
         skills.Finding("not_a_fault", "client_0", "", "", 3),
         skills.Finding("host_incorrect_dns", "ghost_node", "", "", 3)]
    assert skills.submission(f, [], CONTEXT)["root_causes"] == [{"resource_id": "node/dns_pod0", "fault_type": "dns_service_down"}]
