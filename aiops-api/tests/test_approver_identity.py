"""The approval record names the person who is signed in, not whatever name was typed in the request."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import errors, routes_incidents  # noqa: E402


def make(monkeypatch, user):
    seen = {}
    inc = {"id": 7, "status": "awaiting_approval", "owner": "team-pay", "candidates": [{"id": 1, "type": "manual", "params": {}, "label": "x"}]}
    monkeypatch.setattr(routes_incidents.repo, "incident", lambda iid: inc)
    monkeypatch.setattr(routes_incidents.repo, "record_approval", lambda *a, **k: seen.setdefault("approver", a[3]) or 1)
    monkeypatch.setattr(routes_incidents.repo, "set_incident", lambda *a, **k: None)

    async def send(*a, **k):
        return None
    monkeypatch.setattr(routes_incidents.notify, "send", send)
    app = FastAPI()
    errors.install(app)

    @app.middleware("http")
    async def as_user(request: Request, call_next):
        if user:
            request.state.user = user
        return await call_next(request)
    app.include_router(routes_incidents.router)
    return TestClient(app), seen


def test_the_signed_in_person_is_the_approver_whatever_name_is_typed(monkeypatch):
    c, seen = make(monkeypatch, {"id": 2, "name": "Dev Dee", "email": "dev@x.co"})
    r = c.post("/api/v1/incidents/7/approvals", json={"decision": "reject", "approver": "Somebody Else"})
    assert r.status_code == 201 and seen["approver"] == "Dev Dee"


def test_the_typed_name_is_not_needed_once_signed_in(monkeypatch):
    c, seen = make(monkeypatch, {"id": 2, "name": "", "email": "dev@x.co"})
    assert c.post("/api/v1/incidents/7/approvals", json={"decision": "reject"}).status_code == 201
    assert seen["approver"] == "dev@x.co"


def test_without_a_session_the_typed_name_is_used_and_an_empty_one_is_refused(monkeypatch):
    c, seen = make(monkeypatch, None)
    assert c.post("/api/v1/incidents/7/approvals", json={"decision": "reject"}).status_code == 422
    assert c.post("/api/v1/incidents/7/approvals", json={"decision": "reject", "approver": "Ops Ong"}).status_code == 201
    assert seen["approver"] == "Ops Ong"
