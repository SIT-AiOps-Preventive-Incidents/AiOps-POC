"""Turn a host agent's inventory into services, instances and connections.

Connecting a computer is enough to see what runs on it:
  * every listening TCP port -> a "process" service (python3-8000, postgres-5432, ...)
  * every container          -> linked to its traced service if one exists, otherwise a discovered service
  * every established TCP connection to a known listener -> a line on the service map
"""
import re

from . import db, repo

# OS / desktop noise that listens on a port but is not a "service" anyone runs on purpose.
IGNORE_PROCESSES = {
    "controlcenter", "controlce", "rapportd", "sharingd", "identityservicesd", "remoted", "airplayxpchelper",
    "launchd", "mdnsresponder", "usereventagent", "spotify", "dropbox", "onedrive", "systemd", "systemd-resolve",
    "sshd", "cupsd", "chronyd", "rpcbind", "avahi-daemon", "docker-proxy", "containerd", "dockerd", "aiops-agent",
    "com.docker.backend", "figma_agent", "adobe desktop service", "logioptionsplus_agent",
}
DB_PORTS = {5432: "postgres", 3306: "mysql", 6379: "redis", 27017: "mongodb", 9200: "elasticsearch", 5672: "rabbitmq",
            9092: "kafka", 1433: "sqlserver", 1521: "oracle", 11211: "memcached"}
LANG_HINTS = [("python", "python"), ("uvicorn", "python"), ("gunicorn", "python"), ("node", "node"), ("bun", "node"),
              ("deno", "node"), ("java", "java"), ("dotnet", "dotnet"), ("nginx", "nginx"), ("postgres", "postgres"),
              ("redis", "redis"), ("mysqld", "mysql"), ("mongod", "mongodb"), ("ruby", "ruby"), ("php", "php")]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", s.lower()).strip("-")[:40] or "process"


def _lang(*names: str) -> str | None:
    blob = " ".join(n.lower() for n in names if n)
    return next((lang for hint, lang in LANG_HINTS if hint in blob), None)


def _ignored(proc: str, port: int) -> bool:
    p = proc.lower()
    return (p in IGNORE_PROCESSES or "helper" in p  # desktop app helpers (Chrome, VS Code, Discord ...)
            or port >= 49152 or port in (22, 53, 631))


def platform_ignores() -> set[str]:
    raw = db.setting("discovery_ignore_containers") or ""
    return {x.strip() for x in raw.split(",") if x.strip()}


def ingest(host: str, inv: dict) -> dict:
    h = repo.host(host)
    if not h:
        raise KeyError(host)
    owner = h.get("owner")
    ips = sorted(set(inv.get("ips") or []))
    db.ex("UPDATE hosts SET ip_addresses=%s, last_inventory_at=now() WHERE name=%s", (ips, host))

    found, listeners = [], {}  # (port) -> service_name, for matching local connections
    # ---- containers ----
    traced_by_container = {i["container"]: s["service_name"] for s in repo.list_services(("service", "network"))
                           for i in s["instances"] if i.get("container")}
    ignore = platform_ignores()
    for c in inv.get("containers") or []:
        name = c.get("name", "")
        if not name or name in ignore:
            continue
        svc = traced_by_container.get(name)
        if svc:  # already traced: just record that it runs on this host
            repo.ensure_instance(svc, name, host=host, container=name)
            found.append(svc)
            continue
        svc = _slug(name)
        if not repo.service(svc):
            repo.create_service(svc, display_name=name, kind="process", source="discovered",
                                language=_lang(c.get("image", ""), name), owner=owner)
        repo.ensure_instance(svc, name, host=host, container=name)
        found.append(svc)

    # ---- listening processes ----
    for l in inv.get("listeners") or []:
        proc, port = (l.get("process") or "").strip(), int(l.get("port") or 0)
        if not proc or not port or _ignored(proc, port):
            continue
        svc = _slug(f"{proc}-{port}")
        if not repo.service(svc):
            repo.create_service(svc, display_name=f"{proc} :{port}", kind="process", source="discovered",
                                language=_lang(proc, l.get("cmd", "")), owner=owner)
        repo.ensure_instance(svc, f"{host}:{port}", host=host, pid=l.get("pid"), port=port)
        listeners[port] = svc
        found.append(svc)

    # ---- connections -> edges ----
    known_remote = _remote_listeners()
    edges = 0
    for c in inv.get("connections") or []:
        src_port = int(c.get("local_port") or 0)
        rip, rport = c.get("remote_ip", ""), int(c.get("remote_port") or 0)
        src = next((s for p, s in listeners.items() if p == src_port), None) or \
            _service_of_process(listeners, c.get("process"), c.get("pid"), inv)
        if not src:
            continue
        if rip in ("127.0.0.1", "::1") or rip in ips:
            dst = listeners.get(rport)
        else:
            dst = known_remote.get((rip, rport))
            if not dst and rport in DB_PORTS:  # an external database is worth a box even if we do not run it
                dst = f"{DB_PORTS[rport]}-{rip.replace(':', '-')}"
                if not repo.service(dst):
                    repo.create_service(dst, display_name=f"{DB_PORTS[rport]} {rip}:{rport}", kind="external",
                                        source="discovered", language=DB_PORTS[rport], owner=owner)
        if dst and dst != src:
            repo.upsert_connection(src, dst, host)
            edges += 1
    return {"host": host, "services": sorted(set(found)), "edges": edges}


def _service_of_process(listeners: dict, proc: str | None, pid: int | None, inv: dict) -> str | None:
    """A client-only process (no listening port) is attributed to the listener with the same pid, if any."""
    for l in inv.get("listeners") or []:
        if pid and l.get("pid") == pid and int(l.get("port") or 0) in listeners:
            return listeners[int(l["port"])]
    return None


def _remote_listeners() -> dict:
    """(ip, port) -> service for listeners discovered on other connected hosts."""
    out = {}
    for r in db.q("""SELECT h.ip_addresses, i.port, s.service_name FROM service_instances i
                     JOIN hosts h ON h.id=i.host_id JOIN services s ON s.id=i.service_id WHERE i.port IS NOT NULL"""):
        for ip in r["ip_addresses"] or []:
            out[(ip, r["port"])] = r["service_name"]
    return out
