"""Evidence: what the agent reads from each network device, and how it reads it.

Free of NIKA, MCP and any LLM, so it is testable on its own:
  * device_probe / dns_probe - the shell commands the agent runs (read-only, like AIOps One's skill playbooks)
  * parse_device / parse_dns - turn their output into plain facts about one device
The commands use only tools found on a stock Linux / FRR box (ip, tc, iptables, nft, ps, vtysh, dig, getent).
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field

SECTIONS = ["addr", "link", "route", "gwping", "resolv", "qdisc", "fw", "cpu", "dns", "bgp"]


def device_probe() -> str:
    """One command per device. Each section starts with a '##name' line so the parser can split the output."""
    return "; ".join([
        "echo '##addr'; ip -br addr",
        "echo '##link'; ip -br link",
        "echo '##route'; ip route",
        # does the default gateway answer? (one packet, one second)
        "echo '##gwping'; gw=$(ip route | awk '/^default/{print $3; exit}'); "
        "[ -n \"$gw\" ] && (ping -c1 -W1 $gw >/dev/null 2>&1 && echo \"$gw ok\" || echo \"$gw fail\")",
        "echo '##resolv'; grep -E '^nameserver' /etc/resolv.conf 2>/dev/null",
        "echo '##qdisc'; tc qdisc show 2>/dev/null | grep -vE 'noqueue|pfifo_fast|fq_codel|mq ' ",
        "echo '##fw'; (iptables-save 2>/dev/null; nft list ruleset 2>/dev/null) | grep -iE 'drop|reject' | head -n 20",
        "echo '##cpu'; nproc; cut -d' ' -f1 /proc/loadavg; ps -eo pcpu=,comm= --sort=-pcpu 2>/dev/null | head -n 8",
        "echo '##dns'; [ -f /etc/bind/named.conf ] && { pgrep -x named >/dev/null && echo named=up || echo named=down; "
        "grep -hE '^[A-Za-z0-9_-]+[[:space:]]+IN[[:space:]]+A[[:space:]]' /etc/bind/db.* 2>/dev/null | head -n 3; "
        "grep -oE 'zone \"[^\"]+\"' /etc/bind/named.conf | head -n 3; }",
        "echo '##bgp'; command -v vtysh >/dev/null && vtysh -c 'show bgp summary' 2>/dev/null | tail -n 25",
        "true",
    ])


def dns_probe(server_ip: str, name: str) -> str:
    """Ask one DNS server for one name, straight (dig @server) and through the host's own resolver (getent)."""
    return (f"echo '##direct'; dig +tries=1 +time=3 @{server_ip} {name} 2>&1 | grep -E 'status:|Query time|timed out|no servers' ; "
            f"echo '##resolver'; s=$(date +%s%N); getent hosts {name} >/dev/null; rc=$?; "
            f"echo \"rc=$rc ms=$(( ($(date +%s%N) - s) / 1000000 ))\"")


@dataclass
class Device:
    name: str
    addrs: list[ipaddress.IPv4Interface] = field(default_factory=list)
    down_links: list[str] = field(default_factory=list)        # interfaces whose state is DOWN
    default_gw: str | None = None
    gw_answers: bool | None = None
    blackholes: list[str] = field(default_factory=list)        # blackhole / unreachable / prohibit routes
    nameservers: list[str] = field(default_factory=list)
    shaping: list[str] = field(default_factory=list)           # qdisc lines that delay, drop or rate-limit
    drop_rules: list[str] = field(default_factory=list)
    nproc: int = 1
    load1: float = 0.0
    top: list[tuple[float, str]] = field(default_factory=list)  # (cpu %, command)
    dns_server: bool = False
    named_up: bool | None = None
    dns_names: list[str] = field(default_factory=list)         # names this server answers for, e.g. web0.pod0
    bgp_down: list[str] = field(default_factory=list)          # neighbors not Established
    bgp_lines_seen: bool = False
    raw: str = ""

    @property
    def is_router(self) -> bool:
        return bool(re.search(r"router|spine|leaf|switch", self.name)) or bool(self.bgp_lines_seen)

    def owns(self, ip: str) -> bool:
        try:
            return any(a.ip == ipaddress.ip_address(ip) for a in self.addrs)
        except ValueError:
            return False

    def on_link(self, ip: str) -> bool:
        """Is this address inside one of the device's own subnets (i.e. directly reachable)?"""
        try:
            return any(ipaddress.ip_address(ip) in a.network for a in self.addrs)
        except ValueError:
            return False


def split_sections(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    cur = None
    for line in text.splitlines():
        m = re.fullmatch(r"##(\w+)", line.strip())
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur and line.strip():
            out[cur].append(line.rstrip())
    return out


def parse_device(name: str, text: str) -> Device:
    s = split_sections(text)
    d = Device(name=name, raw=text)
    for line in s.get("addr", []):
        for tok in line.split()[2:]:
            try:
                iface = ipaddress.ip_interface(tok)
            except ValueError:
                continue
            if iface.version == 4 and not iface.ip.is_loopback:
                d.addrs.append(iface)
    for line in s.get("link", []):
        cols = line.split()
        if len(cols) >= 2 and cols[0] != "lo" and cols[1] == "DOWN":
            d.down_links.append(cols[0].split("@")[0])
    for line in s.get("route", []):
        if line.startswith("default via "):
            d.default_gw = line.split()[2]
        if re.match(r"(blackhole|unreachable|prohibit)\s", line):
            d.blackholes.append(line.strip())
    for line in s.get("gwping", []):
        cols = line.split()
        if len(cols) == 2:
            d.gw_answers = cols[1] == "ok"
    d.nameservers = [l.split()[1] for l in s.get("resolv", []) if len(l.split()) >= 2]
    d.shaping = [l.strip() for l in s.get("qdisc", []) if re.search(r"\b(netem|tbf|htb|cake|red)\b", l)]
    d.drop_rules = [l.strip() for l in s.get("fw", [])]
    cpu = s.get("cpu", [])
    if cpu:
        d.nproc = int(cpu[0]) if cpu[0].strip().isdigit() else 1
    if len(cpu) > 1:
        try:
            d.load1 = float(cpu[1])
        except ValueError:
            pass
    for line in cpu[2:]:
        m = re.match(r"\s*([\d.]+)\s+(\S+)", line)
        if m:
            d.top.append((float(m.group(1)), m.group(2)))
    dns = s.get("dns", [])
    if dns:
        d.dns_server = True
        d.named_up = "named=up" in dns
        zones = [m.group(1) for l in dns for m in [re.search(r'zone "([^"]+)"', l)] if m]
        hosts = [l.split()[0] for l in dns if re.match(r"[A-Za-z0-9_-]+\s+IN\s+A\s", l)]
        own = [z for z in zones if "arpa" not in z and z != "."]
        d.dns_names = [f"{h}.{own[0]}" for h in hosts] if own else []
    for line in s.get("bgp", []):
        cols = line.split()
        if cols and re.fullmatch(r"\d+\.\d+\.\d+\.\d+|[0-9a-f:]+:[0-9a-f:]*", cols[0]):
            d.bgp_lines_seen = True
            # FRR summary: the State/PfxRcd column is a number when the session is Established
            state = cols[9] if len(cols) > 9 else cols[-1]
            if not re.fullmatch(r"\d+", state) and state not in ("(Policy)",):
                d.bgp_down.append(f"{cols[0]} {state}")
    return d


@dataclass
class DnsCheck:
    client: str
    server_ip: str
    name: str
    direct_ok: bool | None = None
    direct_ms: int | None = None
    resolver_ok: bool | None = None
    resolver_ms: int | None = None


def parse_dns(client: str, server_ip: str, name: str, text: str) -> DnsCheck:
    s = split_sections(text)
    c = DnsCheck(client, server_ip, name)
    direct = " ".join(s.get("direct", []))
    if direct:
        c.direct_ok = "status: NOERROR" in direct
        m = re.search(r"Query time: (\d+)", direct)
        c.direct_ms = int(m.group(1)) if m else None
        if "timed out" in direct or "no servers" in direct:
            c.direct_ok, c.direct_ms = False, None
    for line in s.get("resolver", []):
        m = re.search(r"rc=(\d+) ms=(\d+)", line)
        if m:
            c.resolver_ok, c.resolver_ms = m.group(1) == "0", int(m.group(2))
    return c
