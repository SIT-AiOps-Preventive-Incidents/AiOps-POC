"""Connecting a server from the platform: what AIOps writes on the server and what it accepts from the user."""
from __future__ import annotations

import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import remote  # noqa: E402
from app.api.schemas import SshBulkConnectIn, SshConnectIn  # noqa: E402

PUB = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPlatformKeyForTests aiops@old-comment"


def test_platform_key_can_only_open_the_two_loopback_ports():
    line = remote.tunnel_line(PUB)
    opts, key = line.split(" ", 1)
    assert opts.split(",")[:2] == ["restrict", "port-forwarding"]          # everything else (shell, agent, X11) is off
    assert 'permitlisten="127.0.0.1:18080"' in opts and 'permitlisten="127.0.0.1:14318"' in opts
    assert 'command="/bin/false"' in opts                                  # no shell even if one is asked for
    assert key == "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPlatformKeyForTests aiops-platform"


def test_setup_adds_the_key_once_and_installs_through_the_tunnel():
    s = remote.setup_script("esg360-prod", PUB, ebpf=True)
    assert "grep -qF AAAAC3NzaC1lZDI1NTE5AAAAIPlatformKeyForTests ~/.ssh/authorized_keys ||" in s   # idempotent
    assert "curl -fsSL http://127.0.0.1:18080/install/agent.sh |" in s
    assert "AIOPS_HOST_NAME=esg360-prod AIOPS_API=http://127.0.0.1:18080 AIOPS_OTLP=http://127.0.0.1:14318 sh" in s
    assert "AIOPS_EBPF=0" not in s
    assert "AIOPS_EBPF=0" in remote.setup_script("esg360-prod", PUB, ebpf=False)


def test_setup_quotes_what_the_user_typed():
    s = remote.setup_script("a;rm -rf ~", PUB, ebpf=True)
    assert "AIOPS_HOST_NAME='a;rm -rf ~'" in s


def test_exactly_one_way_to_sign_in():
    base = {"name": "esg360-prod", "address": "34.2.129.3", "user": "poc"}
    assert SshConnectIn(**base, password="x").password == "x"
    assert SshConnectIn(**base, private_key="-----BEGIN OPENSSH PRIVATE KEY-----\n...").port == 22
    with pytest.raises(ValidationError):
        SshConnectIn(**base)
    with pytest.raises(ValidationError):
        SshConnectIn(**base, password="x", private_key="k")


def test_address_and_user_are_plain_names():
    base = {"name": "h", "password": "x"}
    for addr, user in (("34.2.129.3 -oProxyCommand=x", "poc"), ("34.2.129.3", "poc;id"), ("", "poc")):
        with pytest.raises(ValidationError):
            SshConnectIn(**base, address=addr, user=user)


def test_progress_moves_one_step_at_a_time_and_stops_on_failure():
    job = remote.new_job("esg360-prod")
    assert [s["state"] for s in job["steps"]] == ["pending"] * len(remote.STEPS)
    remote.step(job, "connect")
    remote.step(job, "channel")
    assert [s["state"] for s in job["steps"]][:3] == ["done", "running", "pending"]
    remote.fail(job, "port 18080 is already in use on the server")
    assert job["state"] == "failed" and job["steps"][1]["state"] == "failed"
    assert job["error"] == "port 18080 is already in use on the server"


def test_friendly_reason_for_common_ssh_errors():
    assert "password or key" in remote.reason(PermissionError("Permission denied"))
    assert "reach" in remote.reason(TimeoutError())
    assert "18080" in remote.reason(RuntimeError("remote port forwarding failed for listen port 18080"))


def test_bulk_connect_expands_to_one_job_per_host_sharing_one_credential():
    b = SshBulkConnectIn(user="poc", password="s3cret", ebpf=True,
                         targets=[{"address": "10.4.82.40", "name": "db2"},
                                  {"address": "10.4.82.41"}])              # no hostname from discovery
    each = b.each()
    assert [c.name for c in each] == ["db2", "10-4-82-41"]                 # address becomes a valid host name
    assert all(c.password == "s3cret" and c.user == "poc" and c.ebpf for c in each)
    assert all(isinstance(c, SshConnectIn) for c in each)                 # each runs through the single-host path


def test_bulk_connect_needs_exactly_one_credential_and_at_least_one_target():
    with pytest.raises(ValidationError):
        SshBulkConnectIn(user="poc", targets=[{"address": "10.4.82.40"}])                 # no credential
    with pytest.raises(ValidationError):
        SshBulkConnectIn(user="poc", password="x", private_key="y", targets=[{"address": "10.4.82.40"}])  # both
    with pytest.raises(ValidationError):
        SshBulkConnectIn(user="poc", password="x", targets=[])                             # nothing to connect


def test_bulk_route_starts_one_job_per_target_and_reports_them(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api import errors, routes_connect
    started = []

    def fake_start(c):
        started.append(c.name)
        return {"id": f"job-{c.name}"}
    monkeypatch.setattr(routes_connect.remote, "start", fake_start)
    app = FastAPI(); errors.install(app); app.include_router(routes_connect.router)
    r = TestClient(app).post("/api/v1/connect/ssh/bulk", json={
        "user": "poc", "password": "s3cret",
        "targets": [{"address": "10.4.82.40", "name": "db2"}, {"address": "10.4.82.41"}]})
    assert r.status_code == 202
    body = r.json()
    assert body["count"] == 2 and [j["name"] for j in body["jobs"]] == ["db2", "10-4-82-41"]
    assert [j["job_id"] for j in body["jobs"]] == ["job-db2", "job-10-4-82-41"] and started == ["db2", "10-4-82-41"]
