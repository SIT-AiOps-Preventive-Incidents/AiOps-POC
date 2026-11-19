"""/api/v1/network (SNMP discovery mocked, no database, no lab)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import errors, routes_network, routes_platform  # noqa: E402
from app.netdisco import service  # noqa: E402

TOPO = {"nodes": [{"id": "dev:sw-app", "kind": "device"}], "links": [], "events": [], "sources": ["sw-app"], "ts": 1.0}


def client(monkeypatch=None):
    app = FastAPI()
    errors.install(app)
    app.include_router(routes_network.router)
    app.include_router(routes_platform.router)
    return TestClient(app)


def test_get_and_scan(monkeypatch):
    async def cur():
        return TOPO
    calls = []

    async def scan():
        calls.append(1)
        return TOPO
    monkeypatch.setattr(service, "current", cur)
    monkeypatch.setattr(service, "scan", scan)
    monkeypatch.setattr(service, "events", lambda limit=100: [{"id": 1, "kind": "link_down"}])
    c = client(monkeypatch)
    r = c.get("/api/v1/network")
    assert r.status_code == 200 and r.json()["nodes"][0]["id"] == "dev:sw-app" and r.json()["events"][0]["kind"] == "link_down"
    assert c.post("/api/v1/network/scans").status_code == 201 and calls == [1]
    assert c.get("/api/v1/network/events?limit=5").json() == [{"id": 1, "kind": "link_down"}]
