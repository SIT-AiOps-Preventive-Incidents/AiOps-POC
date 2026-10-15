"""What a connected server collects, decided by the platform and sent back to its agent.

One click on Connect gives every container on the server:
  * logs     - an OpenTelemetry Collector on the server reads each container's log file, names it after the
               container's service and ships it over OTLP (JSON lines keep their level),
  * metrics  - the same collector reports per-container CPU, memory and network (docker_stats),
  * traces   - Beyla (eBPF) traces the ports listed by trace_targets(); two apps that listen on the same port
               inside their containers are told apart by their program (node vs java), never guessed.

The type of each container comes from what its image says about itself: official images declare their runtime
in environment variable NAMES (NODE_VERSION, JAVA_HOME, PG_MAJOR ...). Only the names travel, never the values.
"""
import json
import re

OWN = ("aiops-ebpf", "aiops-otelcol")
ENV_RUNTIME = [("NODE_VERSION", "node"), ("JAVA_HOME", "java"), ("JAVA_VERSION", "java"), ("PYTHON_VERSION", "python"),
               ("GOLANG_VERSION", "go"), ("DOTNET_VERSION", "dotnet"), ("ASPNET_VERSION", "dotnet"),
               ("RUBY_VERSION", "ruby"), ("PHP_VERSION", "php"), ("NGINX_VERSION", "nginx"), ("PG_MAJOR", "postgres"),
               ("PG_VERSION", "postgres"), ("MYSQL_VERSION", "mysql"), ("MARIADB_VERSION", "mysql"),
               ("REDIS_VERSION", "redis"), ("MONGO_VERSION", "mongodb")]
NAME_RUNTIME = [("alloy", "go"), ("prometheus", "go"), ("grafana", "go"), ("postgres", "postgres"), ("nginx", "nginx"),
                ("redis", "redis"), ("mysql", "mysql"), ("mariadb", "mysql"), ("mongo", "mongodb"), ("node", "node"),
                ("python", "python"), ("java", "java")]
DATABASES = {"postgres", "mysql", "redis", "mongodb"}
EXE = {"node": "(^|/)node$", "java": "(^|/)java$", "python": "(^|/)python[0-9.]*$", "nginx": "(^|/)nginx$",
       "dotnet": "(^|/)dotnet$", "ruby": "(^|/)ruby[0-9.]*$", "php": "(^|/)php(-fpm)?[0-9.]*$"}
LOG_DIR = "/var/lib/docker/containers"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", s.lower()).strip("-")[:40] or "process"


def container_ports(ports: str) -> list[int]:
    """TCP ports the app listens on inside its container: '127.0.0.1:3001->3000/tcp' -> [3000]."""
    out = []
    for part in (ports or "").split(","):
        m = re.search(r"(\d+)/tcp", part.split("->")[-1])
        if m and int(m.group(1)) not in out:
            out.append(int(m.group(1)))
    return out


def runtime_of(c: dict) -> str | None:
    keys = set(c.get("env_keys") or [])
    for key, rt in ENV_RUNTIME:
        if key in keys:
            return rt
    blob = f"{c.get('image', '')} {c.get('name', '')}".lower()
    return next((rt for hint, rt in NAME_RUNTIME if hint in blob), None)


def _mine(c: dict) -> bool:
    return c.get("name", "") in OWN


def trace_targets(containers: list[dict]) -> list[dict]:
    """eBPF targets: (port, program) pairs that point at exactly one container."""
    by_port: dict[int, list[dict]] = {}
    for c in sorted(containers, key=lambda c: c.get("name", "")):
        rt = runtime_of(c)
        if _mine(c) or rt in DATABASES:
            continue
        for port in container_ports(c.get("ports", "")):
            by_port.setdefault(port, []).append({"service": slug(c["name"]), "port": port, "exe": EXE.get(rt or "")})
    out = []
    for port, cands in sorted(by_port.items()):
        if len(cands) == 1:
            out.append({k: v for k, v in cands[0].items() if v})
            continue
        exes = [c["exe"] for c in cands if c["exe"]]
        out += [c for c in cands if c["exe"] and exes.count(c["exe"]) == 1]
    return out


def config(host: str, containers: list[dict]) -> str:
    """OpenTelemetry Collector config for the server (JSON, which the collector reads as YAML)."""
    receivers, logs = {}, []
    for c in sorted(containers, key=lambda c: c.get("name", "")):
        cid = c.get("id") or ""
        if _mine(c) or not re.fullmatch(r"[0-9a-f]{64}", cid):
            continue
        name = f"filelog/{slug(c['name'])}"
        receivers[name] = {
            "include": [f"{LOG_DIR}/{cid}/{cid}-json.log"], "start_at": "end",
            "resource": {"service.name": slug(c["name"]), "host.name": host},
            "operators": [
                {"type": "container", "format": "docker", "add_metadata_from_filepath": False},
                {"type": "json_parser", "if": 'body matches "^\\\\s*\\\\{"', "parse_to": "attributes",
                 "on_error": "send_quiet"},
                {"type": "severity_parser", "if": "attributes.level != nil", "parse_from": "attributes.level",
                 "on_error": "send_quiet"},
            ]}
        logs.append(name)
    receivers["docker_stats"] = {"endpoint": "unix:///var/run/docker.sock", "collection_interval": "30s",
                                 "api_version": "__DOCKER_API__",   # the agent fills in the server's own version
                                 "excluded_images": ["grafana/beyla*", "otel/opentelemetry-collector*"]}
    proc = ["memory_limiter", "resource/host", "batch"]
    pipelines = {"metrics": {"receivers": ["docker_stats"], "processors": proc, "exporters": ["otlphttp"]}}
    if logs:
        pipelines["logs"] = {"receivers": sorted(logs), "processors": proc, "exporters": ["otlphttp"]}
    return json.dumps({
        "receivers": receivers,
        "processors": {"memory_limiter": {"check_interval": "2s", "limit_mib": 110, "spike_limit_mib": 30},
                       "batch": {"timeout": "5s"},
                       "resource/host": {"attributes": [{"key": "host.name", "value": host, "action": "upsert"}]}},
        "exporters": {"otlphttp": {"endpoint": "__OTLP__"}},
        "service": {"telemetry": {"logs": {"level": "warn"}, "metrics": {"level": "none"}}, "pipelines": pipelines},
    }, indent=1, sort_keys=True)
