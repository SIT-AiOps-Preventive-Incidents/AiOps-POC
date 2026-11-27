"""Read packet evidence for the shop demo from Loki."""
import asyncio
from ipaddress import ip_address

from . import telemetry as tm
from .netdisco import service as netdisco

LOGIN_BURST_SID = 1000001
SHOP_BACKENDS = {"inventory", "payment"}


async def events(sensor: str, kind: str, minutes: int, limit: int, filters: str = "") -> list[dict]:
    selector = f'{{service_name="suricata",service_namespace="{sensor}"}}'
    query = f'| json event_type="event_type"{filters} | event_type = "{kind}" | __error__ = ""'
    return tm.parse_json_lines(await tm.loki_logs(selector, minutes=minutes, limit=limit, line_filter=query))


def _tcp_sample(event: dict) -> dict | None:
    flow = event.get("flow") or {}
    counts = (flow.get("pkts_toserver"), flow.get("pkts_toclient"))
    if any(type(n) is not int or n < 0 for n in counts) or not counts[0]:
        return None
    return {"sent": counts[0], "received": counts[1], "syn": (event.get("tcp") or {}).get("syn") is True}


def _downlink(topo: dict, addresses: set[str]) -> dict | None:
    nodes = {n["id"]: n for n in topo.get("nodes", [])}
    hosts = {n["id"]: n["ip"] for n in nodes.values()
             if n["kind"] == "host" and n.get("ip") in addresses and n.get("status") == "cut off"}
    links = topo.get("links", [])
    for link in links:
        if link["kind"] != "cable" or link["status"] != "down":
            continue
        for access, other in ((link["a"], link["b"]), (link["b"], link["a"])):
            if not nodes[other].get("reachable"):
                continue
            matched = sorted({hosts[l["b"]] for l in links
                              if l["kind"] == "access" and l["a"] == access and l["b"] in hosts})
            if matched:
                return {"ends": [f"{nodes[link[k]]['name']}:{link[k + '_port']}" for k in ("a", "b")], "ips": matched}
    return None


async def investigate(service: str, minutes: int = 5) -> dict:
    if service == "frontend":
        alerts = await events("edge", "alert", minutes, 30,
                              f', sid="alert.signature_id" | sid = "{LOGIN_BURST_SID}"')
        if not alerts:
            return {}
        ips = await tm.container_ip_map()
        for event in alerts:
            flow_id = event.get("flow_id")
            if (ips.get(event.get("dest_ip")) != "edge-fw" or type(flow_id) is not int
                    or (event.get("alert") or {}).get("signature_id") != LOGIN_BURST_SID):
                continue
            source = str(ip_address(event["src_ip"]))
            flows = await events("edge", "flow", minutes, 1, f', fid="flow_id" | fid = "{flow_id}"')
            return {"login_burst": {"wire_source": source, "flow_id": flow_id, "ts": event["ts"],
                                    "packets": _tcp_sample(flows[0]) if flows else None}}
        return {}
    if service != "checkout":
        return {}

    flows = await events("checkout", "flow", minutes, 120, ', dst="dest_port" | dst = "8000"')
    if not flows:
        return {}
    ips = await tm.container_ip_map()
    samples = {}
    for event in flows:
        src, dst = event.get("src_ip"), event.get("dest_ip")
        target = ips.get(dst)
        if (ips.get(src) != "checkout" or target not in SHOP_BACKENDS or event.get("proto") != "TCP"
                or event.get("dest_port") != 8000 or type(event.get("flow_id")) is not int):
            continue
        packets = _tcp_sample(event)
        if packets:
            no_reply = packets["syn"] and packets["received"] == 0
            samples.setdefault((dst, no_reply), {**packets, "source_ip": src, "target_ip": dst, "target": target,
                                                 "flow_id": event["flow_id"], "ts": event["ts"]})
    if not samples:
        return {}

    selected = sorted(samples, key=lambda key: not key[1])[:4]
    unanswered = {dst for dst, no_reply in selected if no_reply}
    result = {"flows": [samples[key] for key in selected]}
    if unanswered:
        stats, topo = await asyncio.gather(events("checkout", "stats", minutes, 1), netdisco.current())
        result["link"] = _downlink(topo, unanswered)
        # An incident can reach RCA before the periodic SNMP scan sees the failure.
        if not result["link"] and any(n.get("ip") in unanswered for n in topo.get("nodes", [])):
            result["link"] = _downlink(await netdisco.scan(), unanswered)
        capture = (stats[0].get("stats") or {}).get("capture", {}) if stats else {}
        if type(capture.get("kernel_drops")) is int:
            result["kernel_drops"] = capture["kernel_drops"]
    return result
