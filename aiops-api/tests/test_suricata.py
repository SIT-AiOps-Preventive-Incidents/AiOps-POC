import asyncio
import json
from unittest.mock import AsyncMock

from app import agent, suricata
from app.api import routes_platform


def test_checkout_tcp_evidence_matches_the_destination_behind_the_cut_link(monkeypatch):
    src, dst = "10.20.1.13", "10.20.2.11"
    flow = {"src_ip": src, "dest_ip": dst, "dest_port": 8000, "proto": "TCP", "flow_id": 2**61 + 7,
            "flow": {"pkts_toserver": 3, "pkts_toclient": 0}, "tcp": {"syn": True}}
    topo = {"nodes": [{"id": "core", "kind": "device", "name": "core-rtr", "reachable": True},
                      {"id": "data", "kind": "device", "name": "sw-data", "reachable": False},
                      {"id": "host", "kind": "host", "ip": dst, "status": "cut off"}],
            "links": [{"kind": "access", "a": "data", "b": "host", "status": "up"},
                      {"kind": "cable", "a": "core", "b": "data", "a_port": "eth2", "b_port": "eth1", "status": "down"}]}
    loki = AsyncMock(side_effect=[[{"line": json.dumps(flow), "ts": 100}],
                                  [{"line": '{"stats":{"capture":{"kernel_drops":0}}}', "ts": 110}]])
    monkeypatch.setattr(suricata.tm, "loki_logs", loki)
    monkeypatch.setattr(suricata.tm, "container_ip_map", AsyncMock(return_value={src: "checkout", dst: "inventory"}))
    cached = {**topo, "links": [topo["links"][0], {**topo["links"][1], "status": "up"}]}
    monkeypatch.setattr(suricata.netdisco, "current", AsyncMock(return_value=cached))
    monkeypatch.setattr(suricata.netdisco, "scan", AsyncMock(return_value=topo))

    evidence = asyncio.run(suricata.investigate("checkout"))
    assert evidence["flows"][0]["flow_id"] == flow["flow_id"]
    assert evidence["link"] == {"ends": ["core-rtr:eth2", "sw-data:eth1"], "ips": [dst]}
    assert evidence["kernel_drops"] == 0
    assert suricata._downlink(topo, {"10.20.2.99"}) is None
    facts = {"suricata": evidence, "alerting_service": "checkout", "error_origin_service": "inventory",
             "unanswered_calls": [{"caller": "checkout", "call": "POST", "traces": 2}], "unanswered_callee": "checkout"}
    fallback = agent.fallback_text("error_rate", facts, {"type": "manual", "params": {}})
    assert "cutting checkout off from inventory" in fallback["root_cause"]
    assert "outbound POST span has no downstream server span" in fallback["summary"]
    assert any("0 reverse TCP packets" in line for line in agent.findings("error_rate", facts))


def test_authentication_alert_keeps_packet_source_and_matches_flow_by_full_id(monkeypatch):
    source, edge, proxy = "172.18.0.10", "172.18.0.11", "172.18.0.12"
    fid = 2**61 + 3
    alert = {"src_ip": source, "dest_ip": edge, "flow_id": fid, "alert": {"signature_id": suricata.LOGIN_BURST_SID}}
    loki = AsyncMock(side_effect=[
        [{"line": json.dumps({**alert, "dest_ip": proxy}), "ts": 101}, {"line": json.dumps(alert), "ts": 100}],
        [{"line": '{"flow":{"pkts_toserver":5,"pkts_toclient":4}}', "ts": 105}],
    ])
    monkeypatch.setattr(suricata.tm, "loki_logs", loki)
    monkeypatch.setattr(suricata.tm, "container_ip_map", AsyncMock(return_value={edge: "edge-fw", proxy: "edge-lb"}))
    evidence = asyncio.run(suricata.investigate("frontend"))
    assert evidence["login_burst"]["wire_source"] == source
    assert evidence["login_burst"]["packets"]["received"] == 4
    assert f'fid = "{fid}"' in loki.await_args.kwargs["line_filter"]


def test_uplink_scenario_changes_only_the_lab_uplink_and_can_restore_it(monkeypatch):
    monkeypatch.setattr(routes_platform.datasets, "DATASET", "shop")
    monkeypatch.setattr(routes_platform.tm, "container_ip_map", AsyncMock(return_value={"10.20.255.11": "sw-data"}))
    name = "4: eth2@if13    inet 10.20.255.11/29 brd 10.20.255.15 scope global eth2"
    execute = AsyncMock(side_effect=[(0, name), (0, ""), (0, name), (0, "")])
    monkeypatch.setattr(routes_platform.tm, "container_exec", execute)
    assert "net_link_down" in asyncio.run(routes_platform._scenarios())
    assert asyncio.run(routes_platform.run_scenario("net_link_down"))["status"] == "started"
    asyncio.run(routes_platform._set_netlab_uplink(up=True))
    assert execute.await_args_list[1].args == ("sw-data", ["ip", "link", "set", "dev", "eth2", "down"])
    assert execute.await_args_list[3].args == ("sw-data", ["ip", "link", "set", "dev", "eth2", "up"])
