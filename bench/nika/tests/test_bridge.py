"""The bridge's case list comes straight from NIKA's pool files, ground truth included."""
from __future__ import annotations

import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bridge  # noqa: E402


def test_cases_come_from_nika_pool(tmp_path):
    pool = tmp_path / "benchmark" / "working" / "pool" / "dc_clos"
    pool.mkdir(parents=True)
    (pool / "link_down.yaml").write_text(yaml.safe_dump({"failure": {"fault_type": "link_down", "cases": [
        {"topo_size": "m", "inject": {"host_name": "x"}, "root_causes": []},
        {"topo_size": "s", "inject": {"host_name": "client_0", "intf_name": "eth0"},
         "root_causes": [{"resource": {"kind": "link", "name": "client_0:eth0--super_spine_router_0:eth2"}, "fault_type": "link_down"}]},
    ]}}))
    cases = bridge.load_cases(str(tmp_path), "dc_clos", "s", [("link_down", 0), ("link_down", 5), ("frr_service_down", 0)])
    assert [c["id"] for c in cases] == ["link_down.0"]
    assert cases[0]["inject"] == {"host_name": "client_0", "intf_name": "eth0"}
    assert bridge.resource_id(cases[0]["root_causes"][0]["resource"]) == "link/client_0:eth0--super_spine_router_0:eth2"


def test_resource_ids_match_nika_catalog():
    assert bridge.resource_id({"kind": "interface", "node": "dns_pod0", "name": "eth0"}) == "interface/dns_pod0/eth0"
    assert bridge.resource_id({"kind": "node", "node": "spine_router_0_0"}) == "node/spine_router_0_0"
