"""Skills: the rules that turn device facts into findings, and findings into a submission.

Each rule is ordinary network-operations knowledge (a host whose gateway does not answer, a resolver pointing at
something that is not a DNS server, a firewall rule that drops ICMP ...). A rule names the fault it suggests in plain
words; the mapping to NIKA's fault IDs and resource IDs is the last step, and only IDs NIKA lists are ever submitted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .evidence import Device, DnsCheck

# processes that are expected to be busy on a lab box; anything else near a full core is contention
EXPECTED_BUSY = re.compile(r"^(named|bgpd|zebra|ospfd|bfdd|staticd|python3?|nginx|ps|sh|bash|tcpdump|ping|dig|getent|head|tail|grep|awk|cut|sed|tc|ip|iptables.*|nft|vtysh|sleep|init|tini)$")
SLOW_DNS_MS = 500
HOG_CPU = 30.0   # % of one core, summed over unexpected processes


@dataclass(frozen=True)
class Finding:
    fault: str        # NIKA fault id this finding points at
    node: str
    iface: str = ""   # set for interface / link owned faults
    evidence: str = ""
    weight: int = 2   # 3 = direct proof (config or state is wrong), 2 = strong sign, 1 = symptom only


def endpoints_role(d: Device, clients: set[str]) -> str:
    if d.dns_server:
        return "server"
    return "client" if d.name in clients else "server"


def analyse(devices: dict[str, Device], dns: list[DnsCheck], clients: set[str]) -> list[Finding]:
    """All findings, strongest first. Pure: the same facts always give the same findings."""
    out: list[Finding] = []
    dns_ips = {str(a.ip) for d in devices.values() if d.dns_server for a in d.addrs}
    dns_by_ip = {str(a.ip): d.name for d in devices.values() if d.dns_server for a in d.addrs}

    for d in devices.values():
        for iface in d.down_links:
            out.append(Finding("link_down", d.name, iface, f"{d.name} {iface} is DOWN", 3))
        for r in d.blackholes:
            out.append(Finding("host_static_blackhole", d.name, "", f"{d.name}: route '{r}'", 3))
        for rule in d.drop_rules:
            fault = acl_fault(rule)
            if fault:
                out.append(Finding(fault, d.name, "", f"{d.name} firewall: {rule[:160]}", 3))
        for q in d.shaping:
            m = re.search(r"\bdev (\S+)", q)
            iface = m.group(1) if m else ""
            if "netem" in q and re.search(r"\bdelay\b", q) and d.dns_server:
                out.append(Finding("dns_lookup_latency", d.name, "", f"{d.name}: {q[:160]}", 3))
            elif "netem" in q and re.search(r"\b(loss|corrupt)\b", q):
                out.append(Finding("link_packet_corruption" if "corrupt" in q else "silent_egress_packet_loss",
                                   d.name, iface or "", f"{d.name}: {q[:160]}", 2))
            elif re.search(r"\b(tbf|htb)\b", q) and re.search(r"\brate\b", q):
                out.append(Finding("link_bandwidth_throttling", d.name, iface or "", f"{d.name}: {q[:160]}", 2))
        if not d.is_router and d.default_gw:
            if not d.on_link(d.default_gw) or d.gw_answers is False:
                why = "is outside every local subnet" if not d.on_link(d.default_gw) else "does not answer ping"
                out.append(Finding("host_incorrect_gateway", d.name, "", f"{d.name}: default gateway {d.default_gw} {why}", 3))
        if not d.is_router and not d.dns_server and dns_ips and d.nameservers and not set(d.nameservers) & dns_ips:
            out.append(Finding("host_incorrect_dns", d.name, "",
                               f"{d.name}: resolver {', '.join(d.nameservers)} is not a DNS server here ({', '.join(sorted(dns_ips))})", 3))
        if d.dns_server and d.named_up is False:
            out.append(Finding("dns_service_down", d.name, "", f"{d.name}: named is not running", 3))
        # CPU taken by processes that have no business being busy. Summed, because a container may be capped below
        # one core: four workers sharing half a CPU each show ~12%, together they starve the box.
        busy = [(cpu, cmd) for cpu, cmd in d.top if not EXPECTED_BUSY.match(cmd)]
        total = sum(cpu for cpu, _ in busy)
        if total >= HOG_CPU:
            what = ", ".join(f"{cmd} {cpu:.0f}%" for cpu, cmd in busy[:3]) + f" (total {total:.0f}% CPU)"
            fault = "receiver_resource_contention" if endpoints_role(d, clients) == "client" else "sender_resource_contention"
            out.append(Finding(fault, d.name, "", f"{d.name}: {what}", 2))

    # DNS answered slowly or not at all although named runs and nothing on the box explains it
    for c in dns:
        server = dns_by_ip.get(c.server_ip)
        if not server:
            continue
        slow = (c.direct_ms or 0) >= SLOW_DNS_MS
        if slow and not any(f.node == server for f in out):
            out.append(Finding("dns_lookup_latency", server, "", f"{c.client} -> {server}: answer took {c.direct_ms} ms", 2))
        if c.direct_ok is False and devices[server].named_up and not any(f.node == server for f in out):
            out.append(Finding("dns_port_blocked", server, "", f"{c.client} -> {server}: no answer although named runs", 1))

    seen, uniq = set(), []
    for f in sorted(out, key=lambda f: -f.weight):
        key = (f.fault, f.node, f.iface)
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return uniq


def acl_fault(rule: str) -> str | None:
    """Which kind of traffic a DROP/REJECT rule blocks, as a NIKA fault id. Rules that drop nothing specific give None."""
    r = rule.lower()
    if not re.search(r"\b(drop|reject)\b", r):
        return None
    if re.search(r"\barp\b", r):
        return "arp_acl_block"
    if re.search(r"(dport|sport|port)\D{0,3}179\b", r):
        return "bgp_acl_block"
    if re.search(r"(dport|sport|port)\D{0,3}53\b", r):
        return "dns_port_blocked"
    if re.search(r"(dport|sport|port)\D{0,3}(80|443|8080)\b", r):
        return "http_acl_block"
    if "frag-needed" in r or "fragmentation-needed" in r or "icmp-type 3/4" in r or re.search(r"icmp.*\b3/4\b", r):
        return "icmp_frag_needed_filter_misconfiguration"
    if "icmp" in r:
        return "icmp_acl_block"
    return None


def symptoms(pingmesh: dict) -> list[str]:
    """Pingmesh anomalies as short lines, for the report and for detection when no device shows a cause."""
    return [f"{a.get('source')} -> {a.get('target')}: {a.get('type')} ({a.get('detail')})"
            for a in (pingmesh or {}).get("anomalies", [])]


# ---------------- submission: findings -> NIKA catalog ids ----------------
def resource_for(f: Finding, owner_kind: str, resource_ids: set[str]) -> str | None:
    """The catalog id for a finding, by the owner kind NIKA declares for its fault type."""
    if owner_kind == "link" and f.iface:
        end = f"{f.node}:{f.iface}"
        return next((r for r in sorted(resource_ids) if r.startswith("link/") and end in r[5:].split("--")), None)
    if owner_kind == "interface" and f.iface:
        rid = f"interface/{f.node}/{f.iface}"
        return rid if rid in resource_ids else None
    rid = f"node/{f.node}"
    return rid if rid in resource_ids else None


def submission(findings: list[Finding], symptom_lines: list[str], context: dict, max_causes: int = 2) -> dict:
    """The answer NIKA's submit() takes. Only ids NIKA listed; at most max_causes, strongest first."""
    ontology = {o["id"]: o.get("owner_kind", "node") for o in context.get("fault_ontology", []) if isinstance(o, dict)}
    resource_ids = {r["id"] for r in context.get("resources", []) if isinstance(r, dict)}
    causes = []
    top = max((f.weight for f in findings if f.fault in ontology), default=0)
    for f in findings:
        if f.weight < top:  # submit the best-supported tier only: a weaker extra guess costs precision
            break
        if f.fault not in ontology:
            continue
        rid = resource_for(f, ontology[f.fault], resource_ids)
        if rid and {"resource_id": rid, "fault_type": f.fault} not in causes:
            causes.append({"resource_id": rid, "fault_type": f.fault})
        if len(causes) >= max_causes:
            break
    anomaly = bool(causes) or bool(symptom_lines)
    return {"is_anomaly": anomaly, "root_causes": causes if anomaly else []}
