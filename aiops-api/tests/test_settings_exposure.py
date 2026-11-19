"""GET /settings is readable by every role, so it never carries sign-in settings, and only people who may edit
settings see the Teams webhook URL (it lets anyone post into the channel)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import errors, routes_platform  # noqa: E402

ROWS = {"sensitivity": "normal", "teams_webhook": "https://x.webhook.office.com/abc", "sso_client_secret": "gAAAA-sealed",
        "sso_issuer": "https://accounts.google.com", "password_login": "1"}


def client(monkeypatch, perms):
    monkeypatch.setattr(routes_platform.db, "settings", lambda: dict(ROWS))

    async def status():
        return {}
    monkeypatch.setattr(routes_platform.llm, "status", status)
    app = FastAPI()
    errors.install(app)

    @app.middleware("http")
    async def as_user(request: Request, call_next):
        request.state.user = {"id": 1, "permissions": set(perms)}
        return await call_next(request)
    app.include_router(routes_platform.router)
    return TestClient(app)


def test_sign_in_settings_never_leave_through_settings(monkeypatch):
    s = client(monkeypatch, {"read", "settings.edit"}).get("/api/v1/settings").json()["settings"]
    assert not [k for k in s if k.startswith("sso_") or k == "password_login"]


def test_a_viewer_sees_whether_teams_is_on_but_not_the_webhook(monkeypatch):
    s = client(monkeypatch, {"read"}).get("/api/v1/settings").json()["settings"]
    assert s["teams_webhook"] == "set" and s["sensitivity"] == "normal"
    s = client(monkeypatch, {"read", "settings.edit"}).get("/api/v1/settings").json()["settings"]
    assert s["teams_webhook"] == "https://x.webhook.office.com/abc"
