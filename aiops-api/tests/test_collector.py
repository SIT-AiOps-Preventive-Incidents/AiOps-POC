"""One click on Connect: the platform tells the server's agent what to collect - logs, metrics and traces."""
from __future__ import annotations

import os
import sys

import hashlib
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import collector  # noqa: E402

ID = {n: hashlib.sha256(n.encode()).hexdigest() for n in ("one-esg-360", "metabase", "b3-postgres-v2", "esg-nginx", "icomp-app")}
ESG = [  # what the agent reported from the ESG 360 production server
    {"name": "one-esg-360", "image": "one-esg-360:ac300dc8", "ports": "127.0.0.1:3001->3000/tcp",
     "id": ID["one-esg-360"], "env_keys": ["PATH", "NODE_VERSION", "YARN_VERSION", "DATABASE_URL"]},
    {"name": "metabase", "image": "metabase/metabase", "ports": "0.0.0.0:10000->3000/tcp, [::]:10000->3000/tcp",
     "id": ID["metabase"], "env_keys": ["PATH", "JAVA_HOME", "JAVA_VERSION"]},
    {"name": "b3-postgres-v2", "image": "postgres:18", "ports": "5432/tcp", "id": ID["b3-postgres-v2"],
     "env_keys": ["PG_MAJOR", "PG_VERSION", "POSTGRES_PASSWORD"]},
    {"name": "esg-nginx", "image": "nginx:stable", "ports": "0.0.0.0:81->80/tcp", "id": ID["esg-nginx"],
     "env_keys": ["NGINX_VERSION"]},
    {"name": "icomp-app", "image": "icompensation-app:latest", "ports": "0.0.0.0:80->80/tcp", "id": ID["icomp-app"],
     "env_keys": ["PATH"]},
    {"name": "aiops-ebpf", "image": "grafana/beyla:3.38.0", "ports": "", "id": "e" * 64, "env_keys": []},
]


def test_ports_inside_the_container():
    assert collector.container_ports("127.0.0.1:3001->3000/tcp") == [3000]
    assert collector.container_ports("0.0.0.0:80->80/tcp, [::]:80->80/tcp") == [80]
    assert collector.container_ports("5432/tcp") == [5432]
    assert collector.container_ports("53/udp, 8080/tcp") == [8080]
    assert collector.container_ports("") == []


def test_type_comes_from_the_image_not_the_name():
    rt = {c["name"]: collector.runtime_of(c) for c in ESG}
    assert rt["one-esg-360"] == "node" and rt["metabase"] == "java"
    assert rt["b3-postgres-v2"] == "postgres" and rt["esg-nginx"] == "nginx"
    assert rt["icomp-app"] is None                               # nothing says what it is: unknown, not a guess
    assert collector.runtime_of({"name": "api", "image": "acme/api", "env_keys": ["PYTHON_VERSION"]}) == "python"
    assert collector.runtime_of({"name": "grafana-alloy", "image": "grafana/alloy:v1.4.2", "env_keys": []}) == "go"


def test_two_apps_on_the_same_port_are_told_apart_by_their_program():
    t = {x["service"]: x for x in collector.trace_targets(ESG)}
    assert t["one-esg-360"] == {"service": "one-esg-360", "port": 3000, "exe": "*/node"}
    assert t["metabase"] == {"service": "metabase", "port": 3000, "exe": "*/java"}
    assert t["esg-nginx"]["exe"] == "*/nginx"
    assert "b3-postgres-v2" not in t                             # databases give no request spans
    assert "icomp-app" not in t                                  # port 80 is shared and its program is unknown
    assert "aiops-ebpf" not in t


def test_ambiguous_same_port_same_program_is_skipped():
    two = [{"name": "a", "image": "x", "ports": "3000/tcp", "id": "a" * 64, "env_keys": ["NODE_VERSION"]},
           {"name": "b", "image": "y", "ports": "3000/tcp", "id": "b" * 64, "env_keys": ["NODE_VERSION"]}]
    assert collector.trace_targets(two) == []


def test_collector_reads_every_container_log_under_its_service_name():
    cfg = json.loads(collector.config("esg360-prod", ESG))   # JSON is valid YAML for the collector
    logs = {k: v for k, v in cfg["receivers"].items() if k.startswith("filelog/")}
    assert set(logs) == {"filelog/one-esg-360", "filelog/metabase", "filelog/b3-postgres-v2", "filelog/esg-nginx",
                         "filelog/icomp-app"}                    # not the agent's own containers
    esg = logs["filelog/one-esg-360"]
    assert esg["include"] == [f"/var/lib/docker/containers/{ID['one-esg-360']}/{ID['one-esg-360']}-json.log"]
    assert esg["resource"] == {"service.name": "one-esg-360", "host.name": "esg360-prod"}
    assert esg["operators"][0]["type"] == "container"
    assert cfg["exporters"]["otlphttp"]["endpoint"] == "%OTLP%"     # the agent fills in its own way out
    assert cfg["service"]["pipelines"]["logs"]["receivers"] == sorted(logs)
    assert "docker_stats" in cfg["service"]["pipelines"]["metrics"]["receivers"]
    assert cfg["processors"]["memory_limiter"]["limit_mib"] <= 120


def test_config_is_stable_so_the_agent_restarts_nothing_when_nothing_changed():
    assert collector.config("h", ESG) == collector.config("h", list(reversed(ESG)))


def test_no_environment_values_are_needed():
    assert all("=" not in k for c in ESG for k in c["env_keys"])   # names only, never DATABASE_URL's value


def test_placeholders_survive_the_installer():
    """/install/aiops-agent.py rewrites __API__ and __OTLP__ in the agent, so the collector placeholders must differ."""
    agent = open(os.path.join(os.path.dirname(__file__), "..", "app", "agent_dist", "aiops-agent.py")).read()
    for ph in ("%OTLP%", "%DOCKER_API%"):
        assert ph in collector.config("h", ESG) and ph in agent
    assert "__OTLP__" not in collector.config("h", ESG) and "__API__" not in collector.config("h", ESG)
