"""/api/v1/cloud (store and provider mocked: no database, no cloud)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import cloud, cloudinv  # noqa: E402
from app.api import errors, routes_cloud  # noqa: E402

GOOD = {"provider": "openstack", "name": "GIST Starships", "config": {"auth_url": "https://keystone.gist/v3"},
        "secret": {"application_credential_id": "id", "application_credential_secret": "s3cret"}}


def client():
    app = FastAPI()
    errors.install(app)
    app.include_router(routes_cloud.router)
    return TestClient(app)


def test_providers_list_what_each_cloud_needs():
    r = client().get("/api/v1/cloud/providers")
    assert r.status_code == 200
    p = {x["id"]: x for x in r.json()}
    assert {"openstack", "vcd", "cloudstack", "aws", "azure", "gcp"} <= set(p)
    assert p["openstack"]["secret"] == ["application_credential_id", "application_credential_secret"]
    assert "reader" in p["openstack"]["role"]


def test_add_account_tests_the_credential_first_and_never_echoes_the_secret(monkeypatch):
    stored = {}

    async def fetch(provider, config, secret, transport=None):
        assert secret["application_credential_secret"] == "s3cret"
        return [{"instance_id": "1", "name": "web-01", "state": "running", "private_ips": ["10.0.0.1"], "public_ips": [],
                 "networks": ["n"], "zone": None, "size": None, "created_at": None, "tags": {}}]

    def create(provider, name, config, secret):
        stored.update(provider=provider, name=name, config=config, secret=secret)
        return {"id": 3, "provider": provider, "name": name, "config": config, "secret": "sealed", "status": "new",
                "last_sync_at": None, "last_error": None}

    def save(account_id, instances):
        stored["saved"] = (account_id, len(instances))
        return {"added": instances, "removed": [], "changed": []}

    monkeypatch.setattr(cloud, "fetch", fetch)
    monkeypatch.setattr(cloudinv, "create", create)
    monkeypatch.setattr(cloudinv, "save_sync", save)
    monkeypatch.setattr(cloudinv, "get", lambda i: {"id": 3, "provider": "openstack", "name": "GIST Starships",
                                                    "config": GOOD["config"], "secret": "sealed", "status": "ok",
                                                    "last_sync_at": 1.0, "last_error": None, "instance_count": 1})
    r = client().post("/api/v1/cloud/accounts", json=GOOD)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["account"]["has_secret"] is True and "secret" not in body["account"]
    assert "s3cret" not in r.text and body["sync"] == {"instances": 1, "added": 1, "removed": 0, "changed": 0}
    assert stored["secret"]["application_credential_secret"] == "s3cret" and stored["saved"] == (3, 1)


def test_a_bad_credential_is_refused_and_nothing_is_stored(monkeypatch):
    async def fetch(*a, **k):
        raise cloud.CloudError("Keystone login: the provider rejected the credential (HTTP 401).")
    calls = []
    monkeypatch.setattr(cloud, "fetch", fetch)
    monkeypatch.setattr(cloudinv, "create", lambda *a: calls.append(a))
    r = client().post("/api/v1/cloud/accounts", json=GOOD)
    assert r.status_code == 422 and "rejected" in r.json()["error"]["message"] and calls == []


def test_invalid_input_is_422_with_the_reasons():
    r = client().post("/api/v1/cloud/accounts", json={**GOOD, "config": {"auth_url": "http://plain/v3"}, "secret": {}})
    assert r.status_code == 422
    msg = r.json()["error"]["message"]
    assert "https" in msg and "credential" in msg
    assert client().post("/api/v1/cloud/accounts", json={**GOOD, "name": " "}).status_code == 422


def test_accounts_are_listed_without_secrets(monkeypatch):
    monkeypatch.setattr(cloudinv, "accounts", lambda: [{"id": 1, "provider": "aws", "name": "prod", "config": {"region": "ap-southeast-7"},
                                                        "secret": "sealed", "status": "ok", "last_sync_at": 1.0, "last_error": None}])
    r = client().get("/api/v1/cloud/accounts")
    assert r.status_code == 200 and "sealed" not in r.text and r.json()[0]["provider_label"] == "Amazon Web Services"


def test_instances_carry_the_cloud_vs_agent_verdict(monkeypatch):
    async def inst(account_id=None):
        return [{"account_id": 1, "instance_id": "a", "name": "web", "state": "running", "private_ips": ["10.0.0.1"],
                 "public_ips": [], "networks": [], "aiops_host": "web", "host_status": "down", "gone_at": None}]
    monkeypatch.setattr(cloudinv, "instances", inst)
    (row,) = client().get("/api/v1/cloud/instances").json()
    assert row["verdict"]["code"] == "agent_silent"


def test_sync_and_delete(monkeypatch):
    async def sync(i):
        return {"instances": 2, "added": 0, "removed": 1, "changed": 1}
    gone = []
    monkeypatch.setattr(cloudinv, "get", lambda i: {"id": i} if i == 1 else None)
    monkeypatch.setattr(cloudinv, "sync", sync)
    monkeypatch.setattr(cloudinv, "delete", lambda i: gone.append(i))
    c = client()
    assert c.post("/api/v1/cloud/accounts/1/sync").json() == {"instances": 2, "added": 0, "removed": 1, "changed": 1}
    assert c.post("/api/v1/cloud/accounts/9/sync").status_code == 404
    assert c.delete("/api/v1/cloud/accounts/1").status_code == 204 and gone == [1]
    assert c.delete("/api/v1/cloud/accounts/9").status_code == 404
