#!/usr/bin/env python3
"""AIOps passive network watcher - LISTENS to ARP only, never sends a packet.

Every machine on a network segment announces "who has / I am" over ARP; those broadcasts reach everyone on the
segment anyway. This keeps the latest (IP, MAC) per interface and writes them to a JSON file the agent reads.
Run by the agent in a container with only CAP_NET_RAW:  python3 netwatch.py /out/neighbors.json
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


def main(out_path: str):
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ARP))
    s.settimeout(5)
    seen = {}
    try:
        seen = {k: v for k, v in json.load(open(out_path)).items()}
    except (OSError, ValueError):
        pass
    last_write = 0.0
    while True:
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
