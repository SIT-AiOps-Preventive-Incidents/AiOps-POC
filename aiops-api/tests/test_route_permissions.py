"""Every route the API really has is named by a permission rule: a new route cannot ship unmapped (it would only
work for admins, silently). Sweeps the real app's routes, so it covers routes added after this test was written."""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.routing import APIRoute  # noqa: E402

from app import rbac  # noqa: E402


def _sample(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "x1", path)


def test_every_api_route_has_a_permission_rule():
    from app.main import app
    missing = [f"{m} {r.path}" for r in app.routes if isinstance(r, APIRoute) for m in r.methods
               if not rbac.mapped(m, _sample(r.path))]
    assert missing == [], "map these in rbac.RULES: " + ", ".join(missing)


def test_nothing_that_changes_data_is_public():
    from app.main import app
    leaks = [f"{m} {r.path}" for r in app.routes if isinstance(r, APIRoute) for m in r.methods
             if m in ("POST", "PUT", "PATCH", "DELETE") and rbac.route_permission(m, _sample(r.path)) == rbac.PUBLIC
             and not r.path.startswith("/api/v1/auth/login")]
    assert leaks == []
