"""Roles and permissions: the matrix (role x permission, like Jenkins' matrix authorization) and which permission
every API call needs. Pure: no database."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import rbac  # noqa: E402


# ------------------------------------------------------------------ the catalog
def test_every_permission_has_a_group_and_a_label_and_ids_are_unique():
    ids = [p["id"] for p in rbac.PERMISSIONS]
    assert len(ids) == len(set(ids))
    assert all(p["group"] in rbac.GROUPS and p["label"] and p["help"] for p in rbac.PERMISSIONS)


def test_the_four_built_in_roles_come_in_order_from_most_to_least():
    assert [r["id"] for r in rbac.ROLES] == ["admin", "management", "developer", "viewer"]


# ------------------------------------------------------------------ the default matrix
def test_admin_can_do_everything_and_cannot_lose_it():
    m = rbac.effective({"admin": []})
    assert m["admin"] == set(rbac.PERMISSION_IDS)


def test_default_matrix_gives_each_role_its_job():
    d = rbac.DEFAULT_MATRIX
    assert d["viewer"] == {"read"}
    # management signs off fixes and owns the incident rules; it does not change the machines or the AI
    assert {"read", "incident.approve", "incident.rate", "automation.playbooks"} <= d["management"]
    assert not d["management"] & {"fleet.connect", "automation.skills", "settings.edit", "demo.run"}
    # developers run the platform day to day; only an admin manages people, sign-in and settings
    assert {"incident.approve", "incident.analyze", "automation.skills", "automation.runbooks", "fleet.connect"} <= d["developer"]
    assert "admin" not in d["developer"] and "settings.edit" not in d["developer"]


def test_every_role_can_read_because_a_role_without_read_cannot_open_the_app():
    m = rbac.effective({"viewer": [], "developer": ["fleet.connect"]})
    assert "read" in m["viewer"] and "read" in m["developer"]


def test_unknown_permissions_in_a_saved_matrix_are_dropped():
    assert rbac.effective({"viewer": ["read", "teleport"]})["viewer"] == {"read"}


def test_validate_matrix_refuses_unknown_roles_and_permissions():
    assert rbac.validate_matrix({"viewer": ["read"]}, known_roles={"viewer"}) == []
    errs = rbac.validate_matrix({"ghost": ["read"], "viewer": ["fly"]}, known_roles={"viewer"})
    assert any("ghost" in e for e in errs) and any("fly" in e for e in errs)


def test_role_id_is_a_safe_slug():
    assert rbac.role_id("On-call SRE!") == "on-call-sre"
    assert rbac.validate_role({"id": "", "label": ""})


# ------------------------------------------------------------------ which permission each API call needs
def need(method, path):
    return rbac.route_permission(method, path)


def test_reading_any_page_needs_read():
    for p in ("/api/v1/overview", "/api/v1/incidents", "/api/v1/incidents/7", "/api/v1/insights", "/api/v1/cloud/accounts",
              "/api/v1/skills", "/api/v1/playbooks", "/api/v1/network/graph"):
        assert need("GET", p) == "read", p


def test_actions_need_their_own_permission():
    cases = {
        ("POST", "/api/v1/incidents/7/approvals"): "incident.approve",
        ("POST", "/api/v1/incidents/7/analyses"): "incident.analyze",
        ("PATCH", "/api/v1/incidents/7"): "incident.update",
        ("PUT", "/api/v1/incidents/7/feedback"): "incident.rate",
        ("POST", "/api/v1/skills"): "automation.skills",
        ("PATCH", "/api/v1/skill-sets/2"): "automation.skills",
        ("POST", "/api/v1/runbooks"): "automation.runbooks",
        ("PATCH", "/api/v1/runbooks/3"): "automation.runbooks",
        ("DELETE", "/api/v1/playbooks/1"): "automation.playbooks",
        ("POST", "/api/v1/connect/ssh/bulk"): "fleet.connect",
        ("DELETE", "/api/v1/hosts/db-01"): "fleet.connect",
        ("POST", "/api/v1/services"): "fleet.connect",
        ("POST", "/api/v1/checks"): "fleet.connect",
        ("POST", "/api/v1/hosts/db-01/netscan"): "fleet.scan",
        ("POST", "/api/v1/network/proxmox"): "fleet.scan",
        ("POST", "/api/v1/cloud/accounts"): "fleet.cloud",
        ("DELETE", "/api/v1/cloud/accounts/4"): "fleet.cloud",
        ("PATCH", "/api/v1/settings"): "settings.edit",
        ("POST", "/api/v1/notifications/test"): "settings.edit",
        ("POST", "/api/v1/scenarios/bad_deploy/runs"): "demo.run",
        ("POST", "/api/v1/deployments"): "deploy.write",
        ("GET", "/api/v1/users"): "admin",
        ("PUT", "/api/v1/roles/matrix"): "admin",
        ("PATCH", "/api/v1/auth/sso"): "admin",
    }
    for (m, p), perm in cases.items():
        assert need(m, p) == perm, (m, p)


def test_signing_in_and_the_agents_own_calls_need_no_session():
    for m, p in (("POST", "/api/v1/auth/login"), ("GET", "/api/v1/auth/providers"), ("GET", "/api/v1/auth/sso/start"),
                 ("GET", "/api/v1/auth/sso/callback"), ("GET", "/install/agent.sh"), ("GET", "/api/ping"), ("GET", "/"),
                 ("GET", "/assets/index-abc.js")):
        assert need(m, p) == rbac.PUBLIC, (m, p)
    for m, p in (("PUT", "/api/v1/hosts/db-01"), ("POST", "/api/v1/hosts/db-01/inventory"),
                 ("POST", "/api/v1/hosts/db-01/uninstalled"), ("GET", "/api/v1/health"), ("POST", "/api/hosts/register")):
        assert need(m, p) == rbac.MACHINE, (m, p)


def test_being_signed_in_is_enough_for_your_own_session():
    assert need("GET", "/api/v1/auth/me") == rbac.SIGNED_IN
    assert need("POST", "/api/v1/auth/logout") == rbac.SIGNED_IN


def test_an_api_change_nobody_mapped_falls_back_to_admin_only():
    assert need("POST", "/api/v1/something-new") == "admin"
    assert need("DELETE", "/api/v1/whatever/1") == "admin"


def test_api_docs_need_read():
    assert need("GET", "/docs") == "read" and need("GET", "/openapi.json") == "read"


def test_allowed_checks_the_users_permissions():
    perms = rbac.effective(rbac.DEFAULT_MATRIX)
    assert rbac.allowed(perms["viewer"], "read")
    assert not rbac.allowed(perms["viewer"], "incident.approve")
    assert rbac.allowed(perms["admin"], "anything.at.all")
    assert rbac.allowed(set(), rbac.PUBLIC) and rbac.allowed(set(), rbac.MACHINE)
