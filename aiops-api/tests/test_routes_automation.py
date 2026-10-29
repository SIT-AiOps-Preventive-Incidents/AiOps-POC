"""/api/v1 automation routes: skills, skill sets, written runbooks, playbooks (store mocked)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import automation_store as st  # noqa: E402
from app.api import errors, routes_automation  # noqa: E402

BUILTIN = {"id": "service-error-analysis", "name": "Service error analysis", "builtin": True, "enabled": True,
           "kinds": ["error_rate"], "instructions": "", "tools": ["searchLogs"]}


def client():
    app = FastAPI(); errors.install(app); app.include_router(routes_automation.router)
    return TestClient(app)


def test_catalog_lists_tools_kinds_and_fix_types():
    b = client().get("/api/v1/automation/catalog").json()
    assert "searchLogs" in b["tools"] and "error_rate" in b["kinds"] and "rollback_deployment" in b["fix_types"]


def test_create_a_custom_skill_and_refuse_a_bad_one(monkeypatch):
    saved = {}
    monkeypatch.setattr(st, "skill", lambda sid: None if sid not in saved else {**saved[sid], "id": sid, "builtin": False})
    monkeypatch.setattr(st, "save_skill", lambda sid, b, builtin: saved.__setitem__(sid, b))
    r = client().post("/api/v1/skills", json={"name": "Payments errors", "kinds": ["error_rate"], "tools": ["searchLogs"], "instructions": "Gateway first"})
    assert r.status_code == 201 and r.json()["id"] == "custom-payments-errors"
    assert client().post("/api/v1/skills", json={"name": "", "kinds": [], "tools": ["rm"]}).status_code == 422


def test_a_builtin_skill_can_be_switched_off_and_given_instructions_but_not_deleted(monkeypatch):
    calls = []
    monkeypatch.setattr(st, "skill", lambda sid: BUILTIN if sid == BUILTIN["id"] else None)
    monkeypatch.setattr(st, "save_skill", lambda sid, b, builtin: calls.append((sid, b["enabled"], b["instructions"], builtin)))
    r = client().patch("/api/v1/skills/service-error-analysis", json={"enabled": False, "instructions": "Check nginx"})
    assert r.status_code == 200 and calls == [("service-error-analysis", False, "Check nginx", True)]
    assert client().delete("/api/v1/skills/service-error-analysis").status_code == 409


def test_written_runbook_is_validated_and_must_not_clash(monkeypatch):
    monkeypatch.setattr(st, "signature_taken", lambda sig, except_id=None: sig == "error_rate|checkout|restart_service")
    monkeypatch.setattr(st, "create_runbook", lambda b: 7)
    good = {"title": "Checkout 5xx", "kind": "error_rate", "service": "checkout", "action_type": "rollback_deployment", "steps": ["Roll back"]}
    r = client().post("/api/v1/runbooks", json=good)
    assert r.status_code == 201 and r.json()["id"] == 7
    assert client().post("/api/v1/runbooks", json={**good, "action_type": "restart_service"}).status_code == 409
    assert client().post("/api/v1/runbooks", json={**good, "steps": []}).status_code == 422


def test_playbook_refuses_to_apply_fixes_on_its_own(monkeypatch):
    monkeypatch.setattr(st, "save_playbook", lambda b, pid=None: {"id": 3, **b})
    ok = {"name": "Payments on-call", "trigger": {"kinds": ["error_rate"]}, "actions": {"owner_team": "team-payments", "escalate_after_min": 30}}
    assert client().post("/api/v1/playbooks", json=ok).status_code == 201
    r = client().post("/api/v1/playbooks", json={**ok, "actions": {"auto_apply": True}})
    assert r.status_code == 422 and "approval" in r.json()["error"]["message"]
