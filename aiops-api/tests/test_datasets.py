"""DEMO_DATASET=anomod: which scenarios are offered and where they go (replayer and registry mocked)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import datasets  # noqa: E402
from app.api import errors, routes_platform  # noqa: E402
from app.netdisco import nika  # noqa: E402
from app.netdisco import scenarios as net  # noqa: E402


def client():
    app = FastAPI()
    errors.install(app)
    app.include_router(routes_platform.router)
    return TestClient(app)


async def _no_cases():
    return []


async def _no_reset():
    return None


def anomod_mode(monkeypatch, calls):
    monkeypatch.setattr(nika, "cases", _no_cases)
    monkeypatch.setattr(nika, "reset", _no_reset)
    monkeypatch.setattr(datasets, "DATASET", "anomod")
    monkeypatch.setattr(net, "available", lambda: False)

    async def cases():
        return ["anomod:Svc_Kill_Media", "anomod:Perf_CPU_Contention"]

    async def play(s):
        calls.append(("play", s))

    async def reset():
        calls.append(("reset",))

    async def net_reset():
        calls.append(("net_reset",))
    monkeypatch.setattr(datasets, "replay_cases", cases)
    monkeypatch.setattr(datasets, "play", play)
    monkeypatch.setattr(datasets, "reset", reset)
    monkeypatch.setattr(net, "reset", net_reset)


def test_anomod_mode_offers_replays_not_the_shop(monkeypatch):
    anomod_mode(monkeypatch, [])
    assert client().get("/api/v1/scenarios").json() == ["anomod:Svc_Kill_Media", "anomod:Perf_CPU_Contention", "reset"]


def test_play_and_reset_go_to_the_replayer(monkeypatch):
    calls = []
    anomod_mode(monkeypatch, calls)
    c = client()
    assert c.post("/api/v1/scenarios/anomod:Svc_Kill_Media/runs").status_code == 202
    assert c.post("/api/v1/scenarios/anomod:Nope/runs").status_code == 404
    r = c.post("/api/v1/scenarios/reset/runs")
    assert r.status_code == 202 and r.json()["status"] == "reset"
    assert calls == [("play", "anomod:Svc_Kill_Media"), ("net_reset",), ("reset",)]


def test_shop_mode_has_no_replays(monkeypatch):
    monkeypatch.setattr(nika, "cases", _no_cases)
    monkeypatch.setattr(datasets, "DATASET", "shop")
    monkeypatch.setattr(net, "available", lambda: False)
    listed = client().get("/api/v1/scenarios").json()
    assert "bad_deploy" in listed and not any(s.startswith("anomod:") for s in listed)


def test_every_socialnetwork_service_has_a_lab_host():
    assert len(datasets.SOCIALNETWORK) == 12
    assert {t for *_, t in datasets.SOCIALNETWORK} == {"app", "data"}
    assert datasets.host_of("media-service") == "sn-media-service"
