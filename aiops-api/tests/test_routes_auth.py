"""Sign-in routes, the access guard on every API call, people and the permission matrix - against an in-memory
store, so no database is needed."""
from __future__ import annotations

import os
import sys
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import auth, rbac  # noqa: E402
from app.api import errors, guard, routes_auth  # noqa: E402


class FakeStore:
    """Just enough of auth_store, in memory."""

    def __init__(self):
        self.users = {
            1: {"id": 1, "email": "admin@x.co", "name": "Ann", "role": "admin", "active": True, "pw": auth.hash_password("admin password 1"), "sso": None},
            2: {"id": 2, "email": "dev@x.co", "name": "Dev", "role": "developer", "active": True, "pw": auth.hash_password("dev password 12"), "sso": None},
            3: {"id": 3, "email": "view@x.co", "name": "Vee", "role": "viewer", "active": True, "pw": auth.hash_password("view password 1"), "sso": None},
        }
        self.sessions, self.log, self.pending = {}, [], {}
        self.raw = {r: set(p) for r, p in rbac.DEFAULT_MATRIX.items()}
        self.role_rows = [{**r, "users": 0} for r in rbac.ROLES]
        self.sso = {"sso_enabled": False, "sso_issuer": "", "sso_client_id": "", "sso_label": "Sign in with SSO",
                    "sso_default_role": "viewer", "sso_role_rules": [], "sso_allowed_domains": "", "password_login": True,
                    "has_secret": False}

    # people
    def _pub(self, u):
        return {k: v for k, v in u.items() if k not in ("pw", "sso")} | {"role_label": u["role"].title(), "has_password": bool(u["pw"])}

    def users_list(self):
        return [self._pub(u) for u in self.users.values()]

    def user(self, uid):
        u = self.users.get(uid)
        return self._pub(u) if u else None

    def user_by_email(self, email):
        u = next((u for u in self.users.values() if u["email"] == email.lower()), None)
        return u and {**u, "role_id": u["role"], "password_hash": u["pw"]}

    def active_admins(self, except_id=None):
        return sum(1 for u in self.users.values() if u["role"] == "admin" and u["active"] and u["id"] != except_id)

    def create_user(self, email, name, role_id, password, actor):
        uid = max(self.users) + 1
        self.users[uid] = {"id": uid, "email": email, "name": name, "role": role_id, "active": True,
                           "pw": auth.hash_password(password) if password else None, "sso": None}
        return uid

    def update_user(self, uid, b, actor):
        u = self.users[uid]
        u.update({k: v for k, v in b.items() if k in ("name", "active", "role")})
        if b.get("password"):
            u["pw"] = auth.hash_password(b["password"])

    def delete_user(self, uid, actor):
        self.users.pop(uid)

    # sessions
    def start_session(self, uid, via, ip, ua):
        tok, h = auth.new_token()
        self.sessions[h] = (uid, via)
        return tok

    def session_user(self, token):
        if not token or auth.digest(token) not in self.sessions:
            return None
        uid, via = self.sessions[auth.digest(token)]
        u = self.users[uid]
        return None if not u["active"] else {"id": uid, "email": u["email"], "name": u["name"], "role": u["role"],
                                             "role_label": u["role"].title(), "via": via, "has_password": bool(u["pw"])}

    def end_session(self, token):
        self.sessions.pop(auth.digest(token), None)

    # roles
    def roles(self):
        return self.role_rows

    def role(self, rid):
        return next((r for r in self.role_rows if r["id"] == rid), None)

    def matrix(self):
        return rbac.effective(self.raw)

    def permissions(self, rid):
        return self.matrix().get(rid, {"read"})

    def save_matrix(self, m, actor):
        for r, p in m.items():
            if r != "admin":
                self.raw[r] = set(p) | {"read"}
        return {}

    def create_role(self, rid, label, copy_from, actor):
        self.role_rows.append({"id": rid, "label": label, "builtin": False, "users": 0})
        self.raw[rid] = set(self.permissions(copy_from)) if copy_from else {"read"}

    def rename_role(self, rid, label, actor):
        self.role(rid)["label"] = label

    def delete_role(self, rid, actor):
        self.role_rows = [r for r in self.role_rows if r["id"] != rid]

    # sso
    def sso_settings(self):
        return dict(self.sso)

    def save_sso(self, b, actor):
        self.sso.update({k: v for k, v in b.items() if k != "sso_client_secret"})
        if b.get("sso_client_secret"):
            self.sso["has_secret"] = True

    def sso_secret(self):
        return "s3cret"

    def remember_sso(self, state, nonce, verifier):
        self.pending[state] = {"nonce": nonce, "verifier": verifier}

    def take_sso(self, state):
        return self.pending.pop(state, None)

    def sso_user(self, issuer, who, role, default_role):
        u = next((u for u in self.users.values() if u["sso"] == (issuer, who["subject"])), None)
        if not u:
            uid = self.create_user(who["email"], who["name"], role or default_role, None, None)
            u = self.users[uid]
            u["sso"] = (issuer, who["subject"])
        elif role:
            u["role"] = role
        return {**u, "role_id": u["role"]}

    def audit(self, actor, action, detail):
        self.log.append((actor and actor.get("email"), action))

    def access_log(self, limit=100):
        return []


@pytest.fixture
def env(monkeypatch):
    s = FakeStore()
    for name in dir(s):
        if not name.startswith("_") and callable(getattr(s, name)):
            monkeypatch.setattr(routes_auth.st, name if name != "users_list" else "users", getattr(s, name), raising=False)
            monkeypatch.setattr(guard.st, name if name != "users_list" else "users", getattr(s, name), raising=False)
    routes_auth.THROTTLE.__init__()
    app = FastAPI()
    errors.install(app)
    guard.install(app)
    app.include_router(routes_auth.router)

    @app.get("/api/v1/overview")
    async def overview():
        return {"ok": True}

    @app.post("/api/v1/incidents/{iid}/approvals")
    async def approve(iid: int):
        return {"ok": True}

    @app.put("/api/v1/hosts/{name}")
    async def agent_register(name: str):
        return {"ok": True}

    return s, TestClient(app)


def login(c, email, pw):
    return c.post("/api/v1/auth/login", json={"email": email, "password": pw})


# ------------------------------------------------------------------ signing in
def test_sign_in_sets_an_httponly_session_and_me_tells_who_and_what_they_may_do(env):
    _, c = env
    r = login(c, "Dev@x.co", "dev password 12")
    assert r.status_code == 200 and "httponly" in r.headers["set-cookie"].lower()
    me = c.get("/api/v1/auth/me").json()
    assert me["email"] == "dev@x.co" and me["role"] == "developer" and "incident.approve" in me["permissions"]


def test_a_wrong_password_says_nothing_about_which_part_was_wrong(env):
    _, c = env
    a = login(c, "dev@x.co", "wrong password!")
    b = login(c, "nobody@x.co", "wrong password!")
    assert a.status_code == b.status_code == 401 and a.json()["error"]["message"] == b.json()["error"]["message"]


def test_five_wrong_passwords_lock_the_account(env):
    _, c = env
    for _ in range(auth.Throttle.LIMIT):
        login(c, "dev@x.co", "wrong password!")
    r = login(c, "dev@x.co", "dev password 12")
    assert r.status_code == 429


def test_a_blocked_person_cannot_sign_in_and_loses_their_session(env):
    s, c = env
    login(c, "dev@x.co", "dev password 12")
    s.users[2]["active"] = False
    assert c.get("/api/v1/overview").status_code == 401
    assert login(c, "dev@x.co", "dev password 12").status_code == 401


def test_sign_out_ends_the_session(env):
    _, c = env
    login(c, "view@x.co", "view password 1")
    assert c.post("/api/v1/auth/logout").status_code == 204
    assert c.get("/api/v1/overview").status_code == 401


def test_providers_tell_the_login_page_what_to_show_without_a_session(env):
    s, c = env
    s.sso.update(sso_enabled=True, sso_label="Sign in with Microsoft")
    assert c.get("/api/v1/auth/providers").json() == {"password": True, "sso": {"enabled": True, "label": "Sign in with Microsoft"}}


def test_changing_your_own_password_needs_the_current_one(env):
    _, c = env
    login(c, "view@x.co", "view password 1")
    assert c.patch("/api/v1/auth/me", json={"password": "a brand new pass", "current_password": "nope"}).status_code == 403
    assert c.patch("/api/v1/auth/me", json={"password": "short", "current_password": "view password 1"}).status_code == 422
    assert c.patch("/api/v1/auth/me", json={"password": "a brand new pass", "current_password": "view password 1"}).status_code == 200
    assert login(c, "view@x.co", "a brand new pass").status_code == 200


# ------------------------------------------------------------------ the guard on every call
def test_no_session_no_data(env):
    _, c = env
    assert c.get("/api/v1/overview").status_code == 401


def test_the_role_decides_what_a_call_may_do(env):
    _, c = env
    login(c, "view@x.co", "view password 1")
    assert c.get("/api/v1/overview").status_code == 200
    r = c.post("/api/v1/incidents/7/approvals")
    assert r.status_code == 403 and r.json()["error"]["details"]["need"] == "incident.approve"
    login(c, "dev@x.co", "dev password 12")
    assert c.post("/api/v1/incidents/7/approvals").status_code == 200


def test_agents_reach_their_own_calls_without_a_session(env):
    _, c = env
    assert c.put("/api/v1/hosts/db-01").status_code == 200


def test_unticking_a_cell_takes_effect_on_the_next_call(env):
    s, c = env
    login(c, "dev@x.co", "dev password 12")
    s.raw["developer"].discard("incident.approve")
    assert c.post("/api/v1/incidents/7/approvals").status_code == 403


# ------------------------------------------------------------------ people (admin)
def test_only_an_admin_manages_people(env):
    _, c = env
    login(c, "dev@x.co", "dev password 12")
    assert c.get("/api/v1/users").status_code == 403
    login(c, "admin@x.co", "admin password 1")
    assert [u["email"] for u in c.get("/api/v1/users").json()] == ["admin@x.co", "dev@x.co", "view@x.co"]


def test_admin_adds_a_person_with_a_password_or_invites_one_for_sso(env):
    s, c = env
    login(c, "admin@x.co", "admin password 1")
    r = c.post("/api/v1/users", json={"email": "Mgr@X.co", "name": "Mo", "role": "management", "password": "manager pass 1"})
    assert r.status_code == 201 and login(c, "mgr@x.co", "manager pass 1").status_code == 200
    login(c, "admin@x.co", "admin password 1")
    assert c.post("/api/v1/users", json={"email": "sso@x.co", "role": "viewer"}).status_code == 201     # SSO only
    assert c.post("/api/v1/users", json={"email": "dev@x.co", "role": "viewer"}).status_code == 409
    assert c.post("/api/v1/users", json={"email": "bad", "role": "viewer"}).status_code == 422
    assert c.post("/api/v1/users", json={"email": "z@x.co", "role": "pirate"}).status_code == 422
    assert c.post("/api/v1/users", json={"email": "z@x.co", "role": "viewer", "password": "short"}).status_code == 422


def test_the_last_admin_cannot_be_demoted_blocked_or_deleted_and_nobody_deletes_themselves(env):
    _, c = env
    login(c, "admin@x.co", "admin password 1")
    assert c.patch("/api/v1/users/1", json={"role": "viewer"}).status_code == 409
    assert c.patch("/api/v1/users/1", json={"active": False}).status_code == 409
    assert c.delete("/api/v1/users/1").status_code == 409
    assert c.patch("/api/v1/users/2", json={"role": "admin"}).status_code == 200
    assert c.patch("/api/v1/users/1", json={"role": "viewer"}).status_code == 409          # still yourself
    assert c.delete("/api/v1/users/3").status_code == 204


# ------------------------------------------------------------------ the matrix (admin)
def test_the_matrix_lists_groups_permissions_roles_and_ticks(env):
    _, c = env
    login(c, "admin@x.co", "admin password 1")
    m = c.get("/api/v1/roles").json()
    assert m["groups"] == rbac.GROUPS and [p["id"] for p in m["permissions"]] == rbac.PERMISSION_IDS
    assert m["matrix"]["viewer"] == ["read"] and m["locked"] == ["admin"]


def test_saving_the_matrix_keeps_admin_whole_and_refuses_unknown_cells(env):
    s, c = env
    login(c, "admin@x.co", "admin password 1")
    r = c.put("/api/v1/roles/matrix", json={"matrix": {"admin": ["read"], "viewer": ["read", "incident.rate"]}})
    assert r.status_code == 200 and r.json()["matrix"]["viewer"] == ["incident.rate", "read"]
    assert set(r.json()["matrix"]["admin"]) == set(rbac.PERMISSION_IDS)
    assert c.put("/api/v1/roles/matrix", json={"matrix": {"viewer": ["fly"]}}).status_code == 422


def test_a_custom_role_can_be_added_copied_and_removed_but_not_a_built_in_one(env):
    _, c = env
    login(c, "admin@x.co", "admin password 1")
    r = c.post("/api/v1/roles", json={"label": "On-call SRE", "copy_from": "developer"})
    assert r.status_code == 201 and r.json()["id"] == "on-call-sre"
    assert "fleet.connect" in c.get("/api/v1/roles").json()["matrix"]["on-call-sre"]
    assert c.post("/api/v1/roles", json={"label": "On-call SRE"}).status_code == 409
    assert c.delete("/api/v1/roles/viewer").status_code == 409
    assert c.delete("/api/v1/roles/on-call-sre").status_code == 204


# ------------------------------------------------------------------ single sign-on
@pytest.fixture
def idp(env, monkeypatch):
    s, c = env
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    meta = {"issuer": "https://idp.example", "authorization_endpoint": "https://idp.example/auth",
            "token_endpoint": "https://idp.example/token", "jwks_uri": "https://idp.example/keys"}
    s.sso.update(sso_enabled=True, sso_issuer="https://idp.example", sso_client_id="radarops", has_secret=True,
                 sso_role_rules=[{"claim": "groups", "value": "sre", "role": "developer"}])
    seen = {}

    async def discover(issuer):
        return meta

    async def exchange(meta_, code, redirect_uri, verifier, client_id, secret):
        seen.update(code=code, verifier=verifier, redirect_uri=redirect_uri, secret=secret)
        now = int(time.time())
        claims = {"iss": "https://idp.example", "aud": "radarops", "sub": "abc", "email": "nok@x.co", "name": "Nok",
                  "groups": seen.get("groups", []), "nonce": seen["nonce"], "iat": now, "exp": now + 300}
        return {"id_token": jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})}

    async def jwks(meta_):
        return {"keys": [{**jwk, "kid": "k1"}]}

    monkeypatch.setattr(routes_auth, "discover", discover)
    monkeypatch.setattr(routes_auth, "exchange_code", exchange)
    monkeypatch.setattr(routes_auth, "fetch_jwks", jwks)
    return s, c, seen


def start(c, seen):
    r = c.get("/api/v1/auth/sso/start", follow_redirects=False)
    assert r.status_code == 302
    from urllib.parse import parse_qs, urlparse
    q = {k: v[0] for k, v in parse_qs(urlparse(r.headers["location"]).query).items()}
    seen["nonce"] = q["nonce"]
    return q


def test_sso_round_trip_creates_the_person_with_the_role_from_their_group(idp):
    s, c, seen = idp
    seen["groups"] = ["sre"]
    q = start(c, seen)
    r = c.get(f"/api/v1/auth/sso/callback?code=XYZ&state={q['state']}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/#/"
    assert seen["code"] == "XYZ" and seen["secret"] == "s3cret" and seen["verifier"]
    me = c.get("/api/v1/auth/me").json()
    assert me["email"] == "nok@x.co" and me["role"] == "developer" and me["via"] == "sso"


def test_sso_without_a_matching_group_gets_the_default_role(idp):
    s, c, seen = idp
    q = start(c, seen)
    c.get(f"/api/v1/auth/sso/callback?code=XYZ&state={q['state']}", follow_redirects=False)
    assert c.get("/api/v1/auth/me").json()["role"] == "viewer"


def test_a_callback_with_an_unknown_or_reused_state_goes_back_to_login_with_a_reason(idp):
    s, c, seen = idp
    q = start(c, seen)
    c.get(f"/api/v1/auth/sso/callback?code=XYZ&state={q['state']}", follow_redirects=False)
    r = c.get(f"/api/v1/auth/sso/callback?code=XYZ&state={q['state']}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("/#/login?error=")


def test_sso_refuses_an_email_outside_the_allowed_domains(idp):
    s, c, seen = idp
    s.sso["sso_allowed_domains"] = "kmutt.ac.th"
    q = start(c, seen)
    r = c.get(f"/api/v1/auth/sso/callback?code=XYZ&state={q['state']}", follow_redirects=False)
    assert "error=" in r.headers["location"] and c.get("/api/v1/auth/me").status_code == 401


def test_password_sign_in_cannot_be_switched_off_until_an_admin_can_sign_in_with_sso(env):
    s, c = env
    login(c, "admin@x.co", "admin password 1")
    r = c.patch("/api/v1/auth/sso", json={"password_login": False})
    assert r.status_code == 409
    assert c.patch("/api/v1/auth/sso", json={"sso_default_role": "pirate"}).status_code == 422
    assert c.patch("/api/v1/auth/sso", json={"sso_label": "Sign in with KMUTT", "sso_client_secret": "x"}).status_code == 200
    got = c.get("/api/v1/auth/sso").json()
    assert got["sso_label"] == "Sign in with KMUTT" and got["has_secret"] and "sso_client_secret" not in got
    assert got["redirect_uri"].endswith("/api/v1/auth/sso/callback")


def test_the_redirect_url_follows_the_https_front_door_when_set(env, monkeypatch):
    _, c = env
    login(c, "admin@x.co", "admin password 1")
    monkeypatch.setattr(routes_auth, "REDIRECT_BASE", "https://radar.example:8443")
    assert c.get("/api/v1/auth/sso").json()["redirect_uri"] == "https://radar.example:8443/api/v1/auth/sso/callback"


def test_behind_https_the_session_cookie_is_secure(env):
    _, c = env
    caddy = TestClient(c.app, client=("172.18.0.5", 5000))
    r = caddy.post("/api/v1/auth/login", json={"email": "dev@x.co", "password": "dev password 12"}, headers={"x-forwarded-proto": "https"})
    assert "secure" in r.headers["set-cookie"].lower()
    r = login(c, "dev@x.co", "dev password 12")
    assert "secure" not in r.headers["set-cookie"].lower()


# ------------------------------------------------------------------ behind a proxy that puts a path in front
PUBLIC = "https://public.example/capstone26/cp26pt1"
AT_PUBLIC = {"host": "public.example"}
PW = {"email": "dev@x.co", "password": "dev password 12"}


def cookies(r):
    """Every Set-Cookie of the answer as {path: (value, attributes)}."""
    out = {}
    for h in r.headers.get_list("set-cookie"):
        parts = [p.strip() for p in h.split(";")]
        at = {p.split("=")[0].lower(): p.partition("=")[2] for p in parts[1:]}
        out[at["path"]] = (parts[0].partition("=")[2].strip('"'), at)
    return out


@pytest.mark.parametrize("configured", [PUBLIC, PUBLIC + "/", PUBLIC + "//"])
def test_through_the_public_address_the_cookie_is_kept_to_its_path(env, monkeypatch, configured):
    _, c = env
    monkeypatch.setattr(routes_auth, "REDIRECT_BASE", configured)
    got = cookies(c.post("/api/v1/auth/login", json=PW, headers=AT_PUBLIC))
    assert got["/capstone26/cp26pt1/"][0] and "secure" in got["/capstone26/cp26pt1/"][1] and "httponly" in got["/capstone26/cp26pt1/"][1]
    assert got["/"][0] == "" and got["/"][1]["max-age"] == "0"      # no older cookie at the root can win over the new one


def test_directly_on_the_vm_the_cookie_is_at_the_root_and_works_without_https(env, monkeypatch):
    _, c = env
    monkeypatch.setattr(routes_auth, "REDIRECT_BASE", PUBLIC)
    got = cookies(login(c, PW["email"], PW["password"]))
    assert got["/"][0] and "secure" not in got["/"][1] and c.get("/api/v1/auth/me").status_code == 200


@pytest.mark.parametrize("forged", [{"x-app-base": "/evil/"}, {"x-forwarded-prefix": "/evil"}, {"x-forwarded-host": "public.example"},
                                    {"origin": "https://public.example"}, {"host": "public.example.evil.com"}])
def test_nothing_a_caller_sends_can_move_the_cookie_or_make_it_secure(env, monkeypatch, forged):
    _, c = env
    monkeypatch.setattr(routes_auth, "REDIRECT_BASE", PUBLIC)
    got = cookies(c.post("/api/v1/auth/login", json=PW, headers=forged))
    live = {p: a for p, (v, a) in got.items() if v}
    assert list(live) == ["/"] and "secure" not in live["/"]


def test_https_is_believed_from_our_own_proxy_only(env):
    _, c = env
    xfp = {"x-forwarded-proto": "https"}
    inside = TestClient(c.app, client=("172.18.0.5", 5000))
    outside = TestClient(c.app, client=("202.44.9.103", 5000))
    assert "secure" in cookies(inside.post("/api/v1/auth/login", json=PW, headers=xfp))["/"][1]
    assert "secure" not in cookies(outside.post("/api/v1/auth/login", json=PW, headers=xfp))["/"][1]


@pytest.mark.parametrize("headers", [AT_PUBLIC, {}])
def test_signing_out_removes_the_cookie_wherever_it_was_set_and_ends_the_session(env, monkeypatch, headers):
    s, c = env
    monkeypatch.setattr(routes_auth, "REDIRECT_BASE", PUBLIC)
    live = {p: v for p, (v, _) in cookies(c.post("/api/v1/auth/login", json=PW, headers=headers)).items() if v}
    (path, tok), = live.items()
    r = c.post("/api/v1/auth/logout", headers={**headers, "cookie": f"{auth.COOKIE}={tok}"})
    gone = cookies(r)
    assert r.status_code == 204 and path in gone and all(v == "" and a["max-age"] == "0" for v, a in gone.values())
    assert c.get("/api/v1/auth/me", headers={**headers, "cookie": f"{auth.COOKIE}={tok}"}).status_code == 401


@pytest.mark.parametrize("configured", [PUBLIC, PUBLIC + "/"])
def test_single_sign_on_comes_back_to_the_public_address_with_one_slash(env, monkeypatch, configured):
    _, c = env
    login(c, "admin@x.co", "admin password 1")
    monkeypatch.setattr(routes_auth, "REDIRECT_BASE", configured)
    r = c.get("/api/v1/auth/sso/callback?state=nope&code=x", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith(PUBLIC + "/#/login?error=")
    assert c.get("/api/v1/auth/sso").json()["redirect_uri"] == PUBLIC + "/api/v1/auth/sso/callback"


def test_a_public_address_that_is_not_one_is_ignored(env, monkeypatch):
    _, c = env
    monkeypatch.setattr(routes_auth, "REDIRECT_BASE", "https://user:pw@evil.example/a?x=1")
    r = c.get("/api/v1/auth/sso/callback?state=nope&code=x", follow_redirects=False)
    assert r.headers["location"].startswith("/#/login?error=")


def test_the_reason_in_the_address_is_fully_encoded(env):
    _, c = env
    r = c.get("/api/v1/auth/sso/callback", params={"error": "a/b?c=1&d#e <x>"}, follow_redirects=False)
    assert r.headers["location"] == "/#/login?error=a%2Fb%3Fc%3D1%26d%23e%20%3Cx%3E"
