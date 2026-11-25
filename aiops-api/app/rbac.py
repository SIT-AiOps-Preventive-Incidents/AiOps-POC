"""Who may do what: roles, permissions and the matrix between them (role x permission, ticked like Jenkins' matrix
authorization), and the permission every API call needs.

  admin       everything, including people, roles and sign-in. Its row in the matrix is locked on.
  management  sees everything, signs off fixes, rates analyses and owns the playbooks (who gets an incident, when it
              escalates). Does not change machines, the AI's skills or settings.
  developer   runs the platform day to day: approves and re-runs analyses, writes skills and runbooks, connects
              machines and services, scans networks, records deploys, runs demo scenarios.
  viewer      reads every page, changes nothing.

The matrix is data: an admin can tick and untick any cell and add roles. Every role keeps `read`, or it could not
open the app. Every API path maps to one permission here; a call nobody mapped needs `admin` (fail closed), and a
test sweeps the real routes so a new route cannot ship unmapped.

Pure: no database. auth.py and the middleware call these.
"""
from __future__ import annotations

import re

PUBLIC = "@public"         # no session: the sign-in page, the web app's files, agent installers
MACHINE = "@machine"       # called by agents on monitored machines, which have no session
SIGNED_IN = "@signed-in"   # any signed-in person (their own session)

GROUPS = ["Overall", "Incidents", "Automation", "Fleet", "Settings", "Demo"]

PERMISSIONS = [
    {"id": "admin", "group": "Overall", "label": "Administer", "help": "Everything, including people, roles and sign-in"},
    {"id": "read", "group": "Overall", "label": "Read", "help": "Open every page and see every incident"},
    {"id": "incident.approve", "group": "Incidents", "label": "Approve fix", "help": "Approve or reject the fix the AI proposes"},
    {"id": "incident.analyze", "group": "Incidents", "label": "Re-analyze", "help": "Run the AI investigation again"},
    {"id": "incident.update", "group": "Incidents", "label": "Update", "help": "Close, reopen or reassign an incident"},
    {"id": "incident.rate", "group": "Incidents", "label": "Rate", "help": "Rate an analysis and leave feedback"},
    {"id": "automation.skills", "group": "Automation", "label": "Skills", "help": "Write AI skills and skill sets, switch built-ins"},
    {"id": "automation.runbooks", "group": "Automation", "label": "Runbooks", "help": "Write, edit and switch runbooks"},
    {"id": "automation.playbooks", "group": "Automation", "label": "Playbooks", "help": "Who gets an incident and when it escalates"},
    {"id": "fleet.connect", "group": "Fleet", "label": "Connect", "help": "Add or remove machines, services and website checks"},
    {"id": "fleet.scan", "group": "Fleet", "label": "Scan network", "help": "Scan a network segment, read Proxmox"},
    {"id": "fleet.cloud", "group": "Fleet", "label": "Cloud accounts", "help": "Connect and remove cloud accounts"},
    {"id": "deploy.write", "group": "Fleet", "label": "Record deploys", "help": "Tell the platform about a new release"},
    {"id": "settings.edit", "group": "Settings", "label": "Settings", "help": "Detection, notifications and business assumptions"},
    {"id": "demo.run", "group": "Demo", "label": "Run scenarios", "help": "Inject demo faults and send test requests"},
]
PERMISSION_IDS = [p["id"] for p in PERMISSIONS]

ROLES = [
    {"id": "admin", "label": "Admin", "builtin": True},
    {"id": "management", "label": "Management", "builtin": True},
    {"id": "developer", "label": "Developer", "builtin": True},
    {"id": "viewer", "label": "Viewer", "builtin": True},
]

DEFAULT_MATRIX: dict[str, set[str]] = {
    "admin": set(PERMISSION_IDS),
    "management": {"read", "incident.approve", "incident.rate", "automation.playbooks"},
    "developer": {"read", "incident.approve", "incident.analyze", "incident.update", "incident.rate", "automation.skills",
                  "automation.runbooks", "fleet.connect", "fleet.scan", "deploy.write", "demo.run"},
    "viewer": {"read"},
}


def effective(matrix: dict[str, list | set]) -> dict[str, set[str]]:
    """What each role can really do: known permissions only, `read` always, admin always everything."""
    out = {}
    for role, perms in matrix.items():
        got = {p for p in perms if p in PERMISSION_IDS} | {"read"}
        out[role] = set(PERMISSION_IDS) if role == "admin" or "admin" in got else got
    return out


def validate_matrix(matrix: dict, known_roles: set[str]) -> list[str]:
    errs = [f"unknown role '{r}'" for r in matrix if r not in known_roles]
    for r, perms in matrix.items():
        errs += [f"unknown permission '{p}' for {r}" for p in perms if p not in PERMISSION_IDS]
    return errs


def role_id(label: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", label.lower())).strip("-")[:32]


def validate_role(b: dict) -> list[str]:
    errs = []
    if not str(b.get("label") or "").strip():
        errs.append("a role needs a name")
    elif not role_id(b["label"]):
        errs.append("the role name needs at least one letter or digit")
    return errs


def allowed(perms: set[str], need: str) -> bool:
    if need in (PUBLIC, MACHINE):
        return True
    if need == SIGNED_IN:
        return True     # the caller has already checked there is a session
    return "admin" in perms or need in perms


# ---------------- which permission each call needs ----------------
_ANY = "*"
_MUTATE = ("POST", "PUT", "PATCH", "DELETE")

# (methods, path regex, permission). The first match wins, so the specific rules come before the general ones.
RULES: list[tuple[tuple[str, ...] | str, str, str]] = [
    # the web app and what it needs before anyone signs in
    (("GET", "HEAD"), r"/(index\.html)?", PUBLIC),
    (("GET", "HEAD"), r"/(assets|icons|fonts)/.*", PUBLIC),
    (("GET", "HEAD"), r"/(favicon\.svg|favicon\.ico|logo\.svg|robots\.txt)", PUBLIC),
    (("GET",), r"/install/[\w.-]+", PUBLIC),
    (("GET",), r"/api/ping", PUBLIC),
    (("GET",), r"/api/v1/auth/(providers|sso/start|sso/callback)", PUBLIC),
    (("POST",), r"/api/v1/auth/login", PUBLIC),
    # agents on monitored machines
    (("PUT",), r"/api/v1/hosts/[^/]+", MACHINE),
    (("POST",), r"/api/v1/hosts/[^/]+/(inventory|uninstalled)", MACHINE),
    (("GET",), r"/api/v1/health", MACHINE),
    (("POST",), r"/api/hosts/register", MACHINE),
    # your own session
    (("GET",), r"/api/v1/auth/me", SIGNED_IN),
    (("POST",), r"/api/v1/auth/logout", SIGNED_IN),
    (("PATCH",), r"/api/v1/auth/me", SIGNED_IN),
    # people, roles, sign-in
    (_ANY, r"/api/v1/(users|roles)(/.*)?", "admin"),
    (_ANY, r"/api/v1/auth/.*", "admin"),
    # incidents
    (("POST",), r"/api/v1/incidents/[^/]+/approvals", "incident.approve"),
    (("POST",), r"/api/v1/incidents/[^/]+/analyses", "incident.analyze"),
    (("PUT",), r"/api/v1/incidents/[^/]+/feedback", "incident.rate"),
    (("PATCH", "DELETE"), r"/api/v1/incidents/[^/]+", "incident.update"),
    # automation
    (_MUTATE, r"/api/v1/(skills|skill-sets)(/.*)?", "automation.skills"),
    (_MUTATE, r"/api/v1/runbooks(/.*)?", "automation.runbooks"),
    (_MUTATE, r"/api/v1/playbooks(/.*)?", "automation.playbooks"),
    # fleet
    (("POST",), r"/api/v1/hosts/[^/]+/netscan", "fleet.scan"),
    (_MUTATE, r"/api/v1/network/(scans|proxmox)(/.*)?", "fleet.scan"),
    (_MUTATE, r"/api/v1/cloud(/.*)?", "fleet.cloud"),
    (_MUTATE, r"/api/v1/(connect|hosts|services|checks)(/.*)?", "fleet.connect"),
    (("POST",), r"/api/v1/deployments", "deploy.write"),
    # settings and notifications
    (_MUTATE, r"/api/v1/(settings|notifications|teams)(/.*)?", "settings.edit"),
    # demo
    (_MUTATE, r"/api/v1/(scenarios|test-requests)(/.*)?", "demo.run"),
    # reading
    (("POST",), r"/api/v1/page-summary", "read"),
    (("GET", "HEAD"), r"/(docs|redoc|openapi\.json)(/.*)?", "read"),
    (("GET", "HEAD"), r"/api/.*", "read"),
]
_COMPILED = [(m, re.compile(p + r"/?\Z")) for m, p, _ in RULES]


def _rule(method: str, path: str) -> str | None:
    method = method.upper()
    for (methods, rx), (_, _, perm) in zip(_COMPILED, RULES):
        if (methods == _ANY or method in methods) and rx.match(path):
            return perm
    return None


def mapped(method: str, path: str) -> bool:
    """Whether a rule names this call (rather than the admin-only fallback)."""
    return _rule(method, path) is not None


def route_permission(method: str, path: str) -> str:
    perm = _rule(method, path)
    if perm is not None:
        return perm
    if path.startswith("/api/"):
        return "admin"         # a call nobody mapped: admins only, until someone maps it
    return PUBLIC if method.upper() in ("GET", "HEAD") else "admin"   # other paths are the web app's own (history routing)
