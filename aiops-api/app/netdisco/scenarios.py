"""Demo faults for the network lab (netlab/). Each one changes the lab only, and `reset` undoes all of them.

  net_link_down     sw-data's uplink to the core goes down: payment and inventory are cut off from checkout
  net_host_port     sw-data's port toward the payment/inventory segment goes down
  net_rogue_device  a device nobody registered plugs into the app segment and starts talking
"""
from __future__ import annotations

import asyncio
import uuid

from .. import telemetry as tm

NAMES = ["net_link_down", "net_host_port", "net_rogue_device"]
ROGUE_LABEL = "aiops.netlab"
NODE_IMAGE = "aiops-netnode:latest"


def _port_cmd(prefix: str, state: str) -> list[str]:
    """`ip link set <the port holding a prefix.* address> up|down` inside a node."""
    return ["sh", "-c", f"ip link set $(ip -o -4 addr | awk '$4 ~ /^{prefix.replace('.', chr(92) + '.')}/ {{print $2; exit}}') {state}"]


def available() -> bool:
    try:
        tm.docker_client().containers.get("sw-data")
        return True
    except Exception:
        return False


def _rogue():
    tm.docker_client().containers.run(
        NODE_IMAGE, name=f"rogue-{uuid.uuid4().hex[:4]}", detach=True, network="nl-seg-app", mem_limit="32m",
        labels={ROGUE_LABEL: "rogue"}, entrypoint=["sh", "-c", "while true; do ping -c1 -W1 10.20.1.1 >/dev/null; sleep 15; done"])


def _remove_rogues():
    for c in tm.docker_client().containers.list(all=True, filters={"label": f"{ROGUE_LABEL}=rogue"}):
        c.remove(force=True)


async def run(name: str):
    if name == "net_link_down":
        await tm.container_exec("sw-data", _port_cmd("10.20.255.", "down"))
    elif name == "net_host_port":
        await tm.container_exec("sw-data", _port_cmd("10.20.2.", "down"))
    elif name == "net_rogue_device":
        await asyncio.to_thread(_rogue)


async def reset():
    if not available():
        return
    for prefix in ("10.20.255.", "10.20.2."):
        await tm.container_exec("sw-data", _port_cmd(prefix, "up"))
    await asyncio.to_thread(_remove_rogues)
