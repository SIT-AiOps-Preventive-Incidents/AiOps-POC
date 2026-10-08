#!/usr/bin/env python3
"""AIOps host agent - stdlib only, Python 3.8+, macOS and Linux.

Every 15 s it measures CPU, memory, disk and load, and every 30 s the top processes,
then PUSHES them to the platform's OpenTelemetry endpoint (OTLP/HTTP JSON).
Every minute it reports what listens here; the platform answers with the ports worth tracing, and on Linux
the agent traces them with eBPF (Grafana Beyla in a container) - no code change in the apps.
Nothing listens on this machine; it only makes outbound HTTP requests.
"""
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request

VERSION = "1.2.0"
DIR = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(DIR, "config.json")))
HOST, OTLP, API = CFG["host"], CFG["otlp"].rstrip("/"), CFG.get("api", "").rstrip("/")
DARWIN = platform.system() == "Darwin"
NCPU = os.cpu_count() or 1


def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def cpu_pct():
    if DARWIN:
        lines = [l for l in sh(["top", "-l", "2", "-n", "0", "-s", "1"]).splitlines() if l.startswith("CPU usage")]
        m = re.search(r"([\d.]+)% idle", lines[-1]) if lines else None
        return round(100 - float(m.group(1)), 2) if m else None

    def snap():
        f = open("/proc/stat").readline().split()[1:]
        v = [int(x) for x in f]
        return v[3] + v[4], sum(v)
    i1, t1 = snap()
    time.sleep(1)
    i2, t2 = snap()
    return round(100 * (1 - (i2 - i1) / max(t2 - t1, 1)), 2)


def mem_pct():
    if DARWIN:
        total = int(sh(["sysctl", "-n", "hw.memsize"]).strip())
        out = sh(["vm_stat"])
        page = int(re.search(r"page size of (\d+)", out).group(1))

        def pages(label):
            m = re.search(label + r":\s+(\d+)", out)
            return int(m.group(1)) if m else 0
        used = (pages("Pages active") + pages("Pages wired down") + pages("Pages occupied by compressor")) * page
        return round(100 * used / total, 2)
    info = dict(l.split(":", 1) for l in open("/proc/meminfo"))
    tot = int(info["MemTotal"].split()[0])
    avail = int(info["MemAvailable"].split()[0])
    return round(100 * (1 - avail / tot), 2)


def disk_pct():
    path = "/System/Volumes/Data" if DARWIN and os.path.exists("/System/Volumes/Data") else "/"
    u = shutil.disk_usage(path)
    return round(100 * (1 - u.free / u.total), 2)


def top_processes(n=5):
    cmd = ["ps", "-Ao", "pid,pcpu,pmem,comm", "-r"] if DARWIN else ["ps", "-eo", "pid,pcpu,pmem,comm", "--sort=-pcpu"]
    rows = []
    for line in sh(cmd).splitlines()[1:n + 1]:
        parts = line.split(None, 3)
        if len(parts) == 4:
            rows.append({"pid": int(parts[0]), "cpu": float(parts[1]), "mem": float(parts[2]),
                         "name": os.path.basename(parts[3])[:60]})
    return rows


# ---------------- service discovery ----------------
def _split_addr(a):
    a = a.strip().strip("[]")
    host, _, port = a.rpartition(":")
    return host.strip("[]"), int(port) if port.isdigit() else 0


def _lsof(state):
    """macOS: full command names via lsof field output (-F)."""
    out, cur = [], {}
    for line in sh(["lsof", "+c", "0", "-nP", "-iTCP", "-sTCP:" + state, "-Fpcn"]).splitlines():
        tag, val = line[:1], line[1:]
        if tag == "p":
            cur = {"pid": int(val)}
        elif tag == "c":
            cur["process"] = val
        elif tag == "n":
            out.append({**cur, "name": val})
    return out


def _ss(args):
    """Linux: ss output; the users:(("proc",pid=1,...)) part is only present for our own processes."""
    rows = []
    for line in sh(["ss", "-H", "-tn"] + args).splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        m = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
        rows.append({"local": parts[3], "remote": parts[4], "process": m.group(1) if m else "", "pid": int(m.group(2)) if m else None})
    return rows


def ip_addresses():
    if DARWIN:
        return sorted(set(re.findall(r"inet (\d+\.\d+\.\d+\.\d+)", sh(["ifconfig"]))) - {"127.0.0.1"})
    return [x for x in sh(["hostname", "-I"]).split() if ":" not in x]


def inventory():
    listeners, conns = [], []
    if DARWIN:
        for r in _lsof("LISTEN"):
            _, port = _split_addr(r["name"])
            listeners.append({"process": r.get("process", ""), "pid": r.get("pid"), "port": port})
        for r in _lsof("ESTABLISHED"):
            if "->" not in r["name"]:
                continue
            loc, rem = r["name"].split("->", 1)
            _, lport = _split_addr(loc)
            rip, rport = _split_addr(rem)
            conns.append({"process": r.get("process", ""), "pid": r.get("pid"), "local_port": lport,
                          "remote_ip": rip, "remote_port": rport})
    else:
        for r in _ss(["-lp"]):
            _, port = _split_addr(r["local"])
            listeners.append({"process": r["process"], "pid": r["pid"], "port": port})
        for r in _ss(["-p", "state", "established"]):
            _, lport = _split_addr(r["local"])
            rip, rport = _split_addr(r["remote"])
            conns.append({"process": r["process"], "pid": r["pid"], "local_port": lport, "remote_ip": rip, "remote_port": rport})
    seen, uniq = set(), []
    for l in listeners:  # same process often listens on IPv4 and IPv6
        k = (l["process"], l["port"])
        if l["port"] and k not in seen:
            seen.add(k)
            uniq.append(l)
    containers = []
    for line in sh(["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Ports}}"]).splitlines():
        p = line.split("\t")
        if len(p) >= 2:
            containers.append({"name": p[0], "image": p[1], "ports": p[2] if len(p) > 2 else ""})
    return {"ips": ip_addresses(), "listeners": uniq, "connections": conns[:500], "containers": containers}


def push_inventory():
    if not API:
        return
    inv = inventory()
    inv["ebpf"] = EBPF
    req = urllib.request.Request(f"{API}/api/v1/hosts/{HOST}/inventory", data=json.dumps(inv).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    reply = json.loads(urllib.request.urlopen(req, timeout=15).read() or b"{}")
    ebpf_apply(reply.get("instrument") or [])


# ---------------- automatic tracing (eBPF) ----------------
EBPF_IMAGE = CFG.get("ebpf_image", "grafana/beyla:3.38.0")
EBPF_NAME = "aiops-ebpf"
EBPF_CFG = os.path.join(DIR, "ebpf.yml")
EBPF = {"state": "disabled", "services": [], "error": None, "version": EBPF_IMAGE.rsplit(":", 1)[-1]}


def ebpf_blocker():
    """Why automatic tracing cannot run here, or None."""
    if str(CFG.get("ebpf", "auto")).lower() in ("off", "0", "false", "no"):
        return "disabled", "turned off at install (AIOPS_EBPF=0)"
    if DARWIN:
        return "unavailable", "macOS has no eBPF - services are discovered, not traced"
    if not os.path.exists("/sys/kernel/btf/vmlinux"):
        return "unavailable", "kernel has no BTF (needs Linux 5.8+ with CONFIG_DEBUG_INFO_BTF)"
    if not shutil.which("docker") or subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        return "unavailable", "Docker is not installed or this user cannot run it (add the user to the docker group)"
    return None


def ebpf_config(targets):
    lines = ["# generated by aiops-agent - which ports to trace and how each service is named",
             "discovery:", "  exclude_otel_instrumented_services: true", "  instrument:"]
    for t in targets:
        lines += [f"    - open_ports: {int(t['port'])}", f"      name: {json.dumps(t['service'])}"]
    lines += ["ebpf:", "  context_propagation: headers",
              "otel_traces_export:", f"  endpoint: {OTLP}", ""]
    return "\n".join(lines)


def ebpf_apply(targets):
    blocked = ebpf_blocker()
    if blocked:
        EBPF.update(state=blocked[0], error=blocked[1], services=[])
        return
    if not targets:
        sh(["docker", "rm", "-f", EBPF_NAME])
        EBPF.update(state="idle", error=None, services=[])
        return
    cfg = ebpf_config(targets)
    digest = hashlib.sha1((cfg + EBPF_IMAGE).encode()).hexdigest()[:12]
    cur = sh(["docker", "inspect", "-f", '{{index .Config.Labels "aiops.cfg"}} {{.State.Running}}', EBPF_NAME]).split()
    EBPF["services"] = [t["service"] for t in targets]
    if cur == [digest, "true"]:
        EBPF.update(state="running", error=None)
        return
    with open(EBPF_CFG, "w") as f:
        f.write(cfg)
    sh(["docker", "rm", "-f", EBPF_NAME])
    r = subprocess.run(["docker", "run", "-d", "--name", EBPF_NAME, "--restart", "unless-stopped", "--label", f"aiops.cfg={digest}",
                        "--privileged", "--pid=host", "--network=host", "-v", f"{EBPF_CFG}:/config.yml:ro",
                        "-v", "/sys/fs/bpf:/sys/fs/bpf", "-e", "BEYLA_CONFIG_PATH=/config.yml",
                        "-e", f"OTEL_RESOURCE_ATTRIBUTES=host.name={HOST}", EBPF_IMAGE],
                       capture_output=True, text=True, timeout=600)
    if r.returncode == 0:
        EBPF.update(state="starting", error=None)
        print(f"{time.strftime('%H:%M:%S')} eBPF tracing {len(targets)} service(s): {', '.join(EBPF['services'])}", flush=True)
    else:
        EBPF.update(state="error", error=(r.stderr or r.stdout).strip()[-300:])


RESOURCE = {"attributes": [
    {"key": "service.name", "value": {"stringValue": "aiops-agent"}},
    {"key": "host.name", "value": {"stringValue": HOST}},
    {"key": "os.type", "value": {"stringValue": platform.system().lower()}},
    {"key": "host.arch", "value": {"stringValue": platform.machine()}},
    {"key": "aiops.agent.version", "value": {"stringValue": VERSION}},
]}


def post(path, body):
    req = urllib.request.Request(OTLP + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10).read()


def push_metrics(values):
    now = str(time.time_ns())
    metrics = [{"name": "aiops.host." + k, "gauge": {"dataPoints": [{"asDouble": float(v), "timeUnixNano": now}]}}
               for k, v in values.items() if v is not None]
    post("/v1/metrics", {"resourceMetrics": [{"resource": RESOURCE, "scopeMetrics": [
        {"scope": {"name": "aiops-agent", "version": VERSION}, "metrics": metrics}]}]})


def push_log(body):
    post("/v1/logs", {"resourceLogs": [{"resource": RESOURCE, "scopeLogs": [{"scope": {"name": "aiops-agent"},
        "logRecords": [{"timeUnixNano": str(time.time_ns()), "severityText": "INFO",
                        "body": {"stringValue": json.dumps(body)}}]}]}]})


def main():
    print(f"aiops-agent {VERSION} -> {OTLP} as {HOST}", flush=True)
    tick = 0
    while True:
        try:
            vals = {"cpu.utilization": cpu_pct(), "memory.utilization": mem_pct(), "disk.utilization": disk_pct(),
                    "load1": round(os.getloadavg()[0], 2), "cpu.count": NCPU, "up": 1}
            push_metrics(vals)
            if tick % 2 == 0:
                push_log({"type": "top_processes", "host": HOST, "processes": top_processes()})
            if tick % 4 == 0:  # every minute: what runs here and who it talks to
                push_inventory()
        except Exception as e:  # keep running through network blips (e.g. laptop leaves the VPN)
            print(f"{time.strftime('%H:%M:%S')} push failed: {e}", file=sys.stderr, flush=True)
        tick += 1
        time.sleep(15)


if __name__ == "__main__":
    main()
