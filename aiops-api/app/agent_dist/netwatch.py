#!/usr/bin/env python3
"""AIOps network watcher.

By default it only LISTENS to ARP - every machine on a segment announces "who has / I am", and those broadcasts
reach everyone anyway, so listening sees no traffic of our own. It keeps the latest (IP, MAC) per interface in a
JSON file the agent reads. Run in a container with only CAP_NET_RAW:  python3 netwatch.py /out/neighbors.json

Opt-in ACTIVE discovery (off by default): when a file named `scan.request` appears next to the output file, the
watcher does ONE pass of its own directly-connected IPv4 subnets - one ARP "who has" per address, rate-limited -
and the replies land in the same file through the normal listen loop. It only ever asks about addresses on the
segments this machine is already on; it sends nothing to any other network, and it does not touch any service
port. Use it only on networks you are authorised to scan. The platform drops the trigger file when the operator
clicks "Scan this segment" for a host they own.
"""
import json
import os
import socket
import struct
import sys
import time

ETH_P_ARP = 0x0806
SKIP = ("lo", "docker", "br-", "veth", "virbr", "cni", "flannel", "kube", "tun", "tap", "wg", "tailscale", "zt")
KEEP_S = 24 * 3600
SWEEP_MAX = 1024          # never sweep a subnet larger than this many addresses (a /22)
SWEEP_RATE = 50           # ARP requests per second, so a /24 finishes in ~5 s without flooding the segment


def watched(iface: str) -> bool:
    return not iface.startswith(SKIP)


def parse_arp(frame: bytes):
    """Ethernet (optionally 802.1Q-tagged) ARP frame -> (sender ip, sender mac), or None."""
    if len(frame) < 14:
        return None
    off, etype = 12, struct.unpack("!H", frame[12:14])[0]
    if etype == 0x8100 and len(frame) >= 18:
        off, etype = 16, struct.unpack("!H", frame[16:18])[0]
    if etype != ETH_P_ARP:
        return None
    a = frame[off + 2:]
    if len(a) < 28:
        return None
    htype, ptype, hlen, plen = struct.unpack("!HHBB", a[:6])
    if htype != 1 or ptype != 0x0800 or hlen != 6 or plen != 4:
        return None
    mac, ip = a[8:14], a[14:18]
    if ip == b"\x00\x00\x00\x00":
        return None
    return ".".join(str(b) for b in ip), ":".join(f"{b:02x}" for b in mac)


def _local_subnets():
    """(iface, ifindex, own ip, own mac, [host ip ints]) for each directly-connected IPv4 subnet, small enough to sweep."""
    import fcntl
    out = []
    for line in os.popen("ip -o -4 addr show").read().splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[2] != "inet":
            continue
        iface, cidr = parts[1], parts[3]
        if not watched(iface) or "/" not in cidr:
            continue
        ip_s, prefix = cidr.split("/")
        prefix = int(prefix)
        hosts = 1 << (32 - prefix)
        if prefix < 32 - SWEEP_MAX.bit_length() + 1 or hosts > SWEEP_MAX or hosts < 2:
            continue
        own = struct.unpack("!I", socket.inet_aton(ip_s))[0]
        base = own & (0xFFFFFFFF << (32 - prefix))
        targets = [base + i for i in range(1, hosts - 1) if base + i != own]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as tmp:
                idx = socket.if_nametoindex(iface)
                mac = fcntl.ioctl(tmp.fileno(), 0x8927, struct.pack("256s", iface.encode()[:15]))[18:24]
        except OSError:
            continue
        out.append((iface, idx, own, mac, targets))
    return out


def _arp_request(own_ip: int, own_mac: bytes, target_ip: int) -> bytes:
    """One ARP 'who has target_ip' broadcast, asking only about an address on our own segment."""
    eth = b"\xff" * 6 + own_mac + struct.pack("!H", ETH_P_ARP)
    arp = struct.pack("!HHBBH", 1, 0x0800, 6, 4, 1) + own_mac + struct.pack("!I", own_ip) \
        + b"\x00" * 6 + struct.pack("!I", target_ip)
    return eth + arp


def sweep_once(send_sock, out_path: str):
    """One bounded ARP pass of this machine's own subnets. Replies arrive through the listen loop."""
    delay = 1.0 / SWEEP_RATE
    sent = 0
    for iface, idx, own, mac, targets in _local_subnets():
        try:
            send_sock.bind((iface, ETH_P_ARP))
        except OSError:
            pass
        for t in targets:
            try:
                send_sock.sendto(_arp_request(own, mac, t), (iface, ETH_P_ARP))
                sent += 1
            except OSError:
                break
            time.sleep(delay)
    print(f"{time.strftime('%H:%M:%S')} active sweep sent {sent} ARP requests on own subnet(s)", flush=True)


def main(out_path: str):
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ARP))
    s.settimeout(5)
    trigger = os.path.join(os.path.dirname(out_path) or ".", "scan.request")
    seen = {}
    try:
        seen = {k: v for k, v in json.load(open(out_path)).items()}
    except (OSError, ValueError):
        pass
    last_write = 0.0
    while True:
        if os.path.exists(trigger):           # operator asked for one active pass of our own segment
            try:
                os.remove(trigger)
            except OSError:
                pass
            try:
                sweep_once(s, out_path)
            except Exception as e:
                print(f"sweep failed: {e}", flush=True)
        try:
            frame, addr = s.recvfrom(2048)
            iface = addr[0]
            hit = parse_arp(frame) if watched(iface) else None
            if hit:
                ip, mac = hit
                now = time.time()
                cur = seen.get(ip) or {"first_seen": now}
                cur.update(mac=mac, iface=iface, last_seen=now)
                seen[ip] = cur
        except socket.timeout:
            pass
        if time.time() - last_write > 20:
            cutoff = time.time() - KEEP_S
            seen = {k: v for k, v in seen.items() if v["last_seen"] >= cutoff}
            tmp = out_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(seen, f)
            os.replace(tmp, out_path)
            last_write = time.time()


if __name__ == "__main__":
    main(sys.argv[1])
