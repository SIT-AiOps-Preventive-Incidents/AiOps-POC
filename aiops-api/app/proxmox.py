"""Read a Proxmox hypervisor with a read-only API token (role PVEAuditor) and match its VMs to the machines we
found on the wire.

From the hypervisor we learn each VM's real name, which node it runs on, and its pool (its owner/team) - things
you cannot see from inside a guest. We tie that to a discovered machine by the MAC the VM's NIC uses, so the
Fleet view and the agent can reason about VMs that share a node (a noisy neighbour, a failing host) without
installing anything on the guests. Nothing here changes the hypervisor; it only reads.
"""
import re

import httpx

TIMEOUT_S = 10


def auth_header(token_id: str, secret: str) -> dict:
    # a read-only API token, never a password: Proxmox sends it as this one header
    return {"Authorization": f"PVEAPIToken={token_id}={secret}"}


def parse_nodes(resources: list[dict]) -> list[dict]:
    return [{"node": r["node"], "status": r.get("status"), "cpus": r.get("maxcpu"), "mem_bytes": r.get("maxmem")}
            for r in resources if r.get("type") == "node"]


def parse_vms(resources: list[dict]) -> list[dict]:
    out = []
    for r in resources:
        if r.get("type") not in ("qemu", "lxc"):
            continue
        out.append({"vmid": r["vmid"], "name": r.get("name"), "node": r.get("node"), "pool": r.get("pool") or None,
                    "status": r.get("status"), "kind": r["type"], "cpus": r.get("maxcpu"), "mem_bytes": r.get("maxmem")})
    return out


def config_macs(config: dict) -> list[str]:
    """MAC of every NIC a VM config declares (net0=virtio=AA:BB:..,bridge=..)."""
    macs = []
    for key, val in config.items():
        if not key.startswith("net"):
            continue
        m = re.search(r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})", str(val))
        if m:
            macs.append(m.group(1).lower())
    return macs


def mac_to_vm(configs: dict[int, dict]) -> dict[str, int]:
    out = {}
    for vmid, cfg in configs.items():
        for mac in config_macs(cfg):
            out.setdefault(mac, vmid)
    return out


def enrich(neighbors: list[dict], vms: list[dict], mac2vm: dict[str, int]) -> list[dict]:
    """Add name/node/owner from Proxmox to a discovered machine whose MAC belongs to a VM."""
    by_id = {v["vmid"]: v for v in vms}
    out = []
    for n in neighbors:
        vm = by_id.get(mac2vm.get((n.get("mac") or "").lower(), -1))
        if vm:
            n = {**n, "name": vm["name"] or n.get("name"), "node": vm["node"], "owner": vm["pool"], "vmid": vm["vmid"]}
        out.append(n)
    return out


async def fetch(base_url: str, token_id: str, secret: str, verify: bool = True) -> dict:
    """One read-only pass: cluster VMs/nodes and each VM's NIC MACs. base_url like https://pve:8006."""
    headers = auth_header(token_id, secret)
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), headers=headers, timeout=TIMEOUT_S, verify=verify) as c:
        resources = (await c.get("/api2/json/cluster/resources", params={"type": "vm"})).json()["data"]
        node_res = (await c.get("/api2/json/cluster/resources")).json()["data"]
        vms = parse_vms(resources)
        configs = {}
        for v in vms:
            if v["kind"] != "qemu":
                continue
            r = await c.get(f"/api2/json/nodes/{v['node']}/qemu/{v['vmid']}/config")
            if r.status_code == 200:
                configs[v["vmid"]] = r.json().get("data", {})
    return {"nodes": parse_nodes(node_res), "vms": vms, "mac_to_vm": mac_to_vm(configs)}
