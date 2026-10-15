"""Read a Proxmox hypervisor (read-only) and match its VMs to the machines we found on the wire by MAC."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import proxmox  # noqa: E402

RESOURCES = [
    {"id": "node/pve1", "type": "node", "node": "pve1", "status": "online", "maxcpu": 32, "maxmem": 270000000000},
    {"id": "qemu/101", "type": "qemu", "node": "pve1", "vmid": 101, "name": "db2", "status": "running", "pool": "db", "maxcpu": 4, "maxmem": 8589934592},
    {"id": "qemu/102", "type": "qemu", "node": "pve2", "vmid": 102, "name": "app9", "status": "running", "maxcpu": 2, "maxmem": 4294967296},
    {"id": "lxc/200", "type": "lxc", "node": "pve2", "vmid": 200, "name": "ct-cache", "status": "stopped", "pool": "infra"},
    {"id": "storage/pve1/local", "type": "storage", "node": "pve1"},
]
CONFIG_101 = {"net0": "virtio=BC:24:11:00:00:01,bridge=vmbr0,tag=82", "net1": "virtio=BC:24:11:AA:BB:CC,bridge=vmbr1"}


def test_only_vms_and_containers_come_back_with_their_node_and_owner():
    vms = proxmox.parse_vms(RESOURCES)
    assert {v["vmid"] for v in vms} == {101, 102, 200}
    db = next(v for v in vms if v["vmid"] == 101)
    assert db == {"vmid": 101, "name": "db2", "node": "pve1", "pool": "db", "status": "running", "kind": "qemu",
                  "cpus": 4, "mem_bytes": 8589934592}
    assert next(v for v in vms if v["vmid"] == 102)["pool"] is None     # a VM in no pool is allowed


def test_nodes_are_listed_with_capacity():
    nodes = proxmox.parse_nodes(RESOURCES)
    assert nodes == [{"node": "pve1", "status": "online", "cpus": 32, "mem_bytes": 270000000000}]


def test_every_mac_a_vm_uses_maps_back_to_it():
    assert proxmox.config_macs(CONFIG_101) == ["bc:24:11:00:00:01", "bc:24:11:aa:bb:cc"]
    m = proxmox.mac_to_vm({101: CONFIG_101, 102: {"net0": "e1000=BC:24:11:00:00:02,bridge=vmbr0"}})
    assert m["bc:24:11:00:00:01"] == 101 and m["bc:24:11:00:00:02"] == 102


def test_a_discovered_machine_is_named_and_owned_from_proxmox_not_guessed():
    neighbors = [{"ip": "10.4.82.40", "mac": "BC:24:11:00:00:01", "name": None},
                 {"ip": "10.4.82.99", "mac": "aa:bb:cc:dd:ee:ff", "name": None}]
    vms = proxmox.parse_vms(RESOURCES)
    mac2vm = proxmox.mac_to_vm({101: CONFIG_101})
    out = {n["ip"]: n for n in proxmox.enrich(neighbors, vms, mac2vm)}
    assert out["10.4.82.40"]["name"] == "db2" and out["10.4.82.40"]["node"] == "pve1" and out["10.4.82.40"]["owner"] == "db"
    assert out["10.4.82.99"].get("node") is None                        # not a Proxmox VM: left as it was


def test_auth_header_is_a_read_only_api_token_never_a_password():
    h = proxmox.auth_header("aiops@pve!readonly", "SECRET-UUID")
    assert h == {"Authorization": "PVEAPIToken=aiops@pve!readonly=SECRET-UUID"}
