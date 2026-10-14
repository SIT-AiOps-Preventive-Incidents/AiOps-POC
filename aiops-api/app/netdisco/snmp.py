"""SNMP: read a network device the way discovery tools do, using only standard MIBs.

  SNMPv2-MIB  sysName, sysDescr, sysUpTime          what the device is
  IF-MIB      ifName / ifDescr, ifPhysAddress, ifOperStatus, ifSpeed     its ports and whether they are up
  IP-MIB      ipAdEntIfIndex / ipAdEntNetMask       which subnet each port is on
  IP-MIB      ipNetToMediaPhysAddress / Type        ARP: which hosts it sees on each port
  LLDP-MIB    lldpRemSysName / lldpRemPortId        which device is on the other end of each cable

`walk()` shells out to net-snmp's snmpbulkwalk; everything else is pure parsing, tested on recorded output.
"""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass, field

SYS = ".1.3.6.1.2.1.1"
IF = ".1.3.6.1.2.1.2.2.1"
IFX_NAME = ".1.3.6.1.2.1.31.1.1.1.1"
IP_ADDR = ".1.3.6.1.2.1.4.20.1"
ARP = ".1.3.6.1.2.1.4.22.1"
LLDP_LOC_PORT = ".1.0.8802.1.1.2.1.3.7.1"
LLDP_REM = ".1.0.8802.1.1.2.1.4.1.1"
TABLES = [SYS, IF, IFX_NAME, IP_ADDR, ARP, LLDP_LOC_PORT, LLDP_REM]


@dataclass
class Port:
    index: int
    name: str = ""
    mac: str = ""
    up: bool = True
    admin_up: bool = True
    speed_mbps: int = 0
    ips: list[ipaddress.IPv4Interface] = field(default_factory=list)


@dataclass
class Neighbor:            # one LLDP entry: on my port `port`, the device `system` with its port `remote_port`
    port: str
    system: str
    remote_port: str
    remote_descr: str = ""


@dataclass
class ArpEntry:
    port: str
    ip: str
    mac: str


@dataclass
class Device:
    address: str           # where we polled it (its management address)
    name: str = ""
    descr: str = ""
    uptime_s: int = 0
    ports: dict[int, Port] = field(default_factory=dict)
    arp: list[ArpEntry] = field(default_factory=list)
    neighbors: list[Neighbor] = field(default_factory=list)
    reachable: bool = True
    error: str = ""

    def port_by_name(self, name: str) -> Port | None:
        return next((p for p in self.ports.values() if p.name == name), None)

    @property
    def mgmt_port(self) -> str:
        return next((p.name for p in self.ports.values() if any(str(i.ip) == self.address for i in p.ips)), "")


# ---------------- parsing net-snmp output (-On -Oe -Ot) ----------------
HEX = "\x00hex:"   # marks a Hex-STRING until its wrapped lines are joined
LINE = re.compile(r"^(\.[\d.]+) = (?:([\w-]+): ?)?(.*)$")


def parse_walk(text: str) -> dict[str, str]:
    """'.1.3.6... = TYPE: value' lines -> {oid: value}. Hex strings become 'aa:bb:..', quotes are dropped,
    and a value that wraps onto the next line (long Hex-STRINGs) is joined back."""
    out: dict[str, str] = {}
    last = None
    for raw in text.splitlines():
        m = LINE.match(raw.strip())
        if not m:
            if last and raw.strip() and not raw.startswith("."):
                out[last] += " " + raw.strip()
            continue
        oid, typ, val = m.group(1), (m.group(2) or ""), m.group(3).strip()
        if val.startswith("No Such") or val.startswith("No more variables"):
            continue
        if len(val) >= 2 and val[0] == val[-1] == '"':
            val = val[1:-1]
        out[oid] = HEX + val if typ == "Hex-STRING" else val
        last = oid
    return {k: (hexstr(v[len(HEX):]) if v.startswith(HEX) else v) for k, v in out.items()}


def hexstr(v: str) -> str:
    return ":".join(b.lower() for b in v.split())


def mac(v: str) -> str:
    """'2:42:ac:12:0:3', '02 42 AC 12 00 03' or '02:42:ac:12:00:03' -> '02:42:ac:12:00:03'. Anything else -> ''."""
    parts = re.split(r"[:\s-]", v.strip())
    if len(parts) == 6 and all(re.fullmatch(r"[0-9a-fA-F]{1,2}", p) for p in parts):
        return ":".join(p.lower().zfill(2) for p in parts)
    return ""


def column(rows: dict[str, str], table_col: str) -> dict[str, str]:
    """{index suffix: value} for one column, e.g. column(rows, IF + '.2') -> {'1': 'lo', '2': 'eth0'}."""
    pre = table_col + "."
    return {k[len(pre):]: v for k, v in rows.items() if k.startswith(pre)}


def parse_device(address: str, rows: dict[str, str]) -> Device:
    d = Device(address=address)
    d.name = rows.get(SYS + ".5.0", "") or address
    d.descr = rows.get(SYS + ".1.0", "")
    up = rows.get(SYS + ".3.0", "0")
    d.uptime_s = int(up) // 100 if up.isdigit() else 0
    names = column(rows, IFX_NAME)
    for idx, descr in column(rows, IF + ".2").items():
        if not idx.isdigit():
            continue
        p = Port(int(idx), name=names.get(idx) or descr)
        p.mac = mac(rows.get(f"{IF}.6.{idx}", ""))
        p.up = rows.get(f"{IF}.8.{idx}", "1") == "1"
        p.admin_up = rows.get(f"{IF}.7.{idx}", "1") == "1"
        speed = rows.get(f"{IF}.5.{idx}", "0")
        p.speed_mbps = int(speed) // 1_000_000 if speed.isdigit() else 0
        d.ports[p.index] = p
    masks = column(rows, IP_ADDR + ".3")
    for ip, idx in column(rows, IP_ADDR + ".2").items():
        port = d.ports.get(int(idx)) if idx.isdigit() else None
        if port and ip in masks:
            iface = ipaddress.ip_interface(f"{ip}/{masks[ip]}")
            if not iface.ip.is_loopback:
                port.ips.append(iface)
    types = column(rows, ARP + ".4")
    for key, phys in column(rows, ARP + ".2").items():
        idx, _, ip = key.partition(".")
        port = d.ports.get(int(idx)) if idx.isdigit() else None
        if port and types.get(key, "3") in ("3", "4") and mac(phys):   # dynamic or static; skip invalid (2)
            d.arp.append(ArpEntry(port.name, ip, mac(phys)))
    d.neighbors = parse_lldp(rows, d)
    return d


def parse_lldp(rows: dict[str, str], d: Device) -> list[Neighbor]:
    """lldpRemTable is indexed by (timeMark, localPortNum, remIndex). The local port number is resolved through
    lldpLocPortTable's port id / description to our ifName; lldpd also uses the ifIndex as the number."""
    loc = {}
    for num, pid in column(rows, LLDP_LOC_PORT + ".3").items():
        desc = rows.get(f"{LLDP_LOC_PORT}.4.{num}", "")
        name = next((n for n in (pid, desc) if d.port_by_name(n)), None)
        if name is None and num.isdigit() and int(num) in d.ports:
            name = d.ports[int(num)].name
        loc[num] = name or pid
    out = []
    for key, system in column(rows, LLDP_REM + ".9").items():
        parts = key.split(".")
        if len(parts) != 3:
            continue
        _, num, _ = parts
        port = loc.get(num) or (d.ports[int(num)].name if num.isdigit() and int(num) in d.ports else num)
        out.append(Neighbor(port, system, rows.get(f"{LLDP_REM}.7.{key}", ""), rows.get(f"{LLDP_REM}.8.{key}", "")))
    return out


# ---------------- polling ----------------
async def walk(address: str, community: str = "public", timeout_s: int = 2) -> str:
    """All the tables above in one go. Raises on timeout / unreachable."""
    outs = []
    for oid in TABLES:
        proc = await asyncio.create_subprocess_exec(
            "snmpbulkwalk", "-v2c", "-c", community, "-On", "-Oe", "-Ot", "-t", str(timeout_s), "-r", "1", address, oid,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await proc.communicate()
        if proc.returncode != 0:
            if oid == SYS:            # the device itself does not answer
                raise ConnectionError((err.decode().strip() or "no response").splitlines()[0])
            continue                  # an optional MIB (e.g. no LLDP) is not an error
        outs.append(out.decode(errors="replace"))
    return "\n".join(outs)


async def poll(address: str, community: str = "public") -> Device:
    """Poll one device. A name is resolved first: the management port is recognised by the address we polled."""
    try:
        ip = await asyncio.to_thread(socket.gethostbyname, address)
    except OSError:
        return Device(address=address, name=address, reachable=False, error=f"cannot resolve {address}")
    try:
        return parse_device(ip, parse_walk(await walk(ip, community)))
    except (ConnectionError, OSError) as e:
        return Device(address=ip, name=address, reachable=False, error=str(e))
